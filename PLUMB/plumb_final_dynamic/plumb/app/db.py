from __future__ import annotations
import json, os
from pathlib import Path
from sqlalchemy import create_engine, String, Text, Integer, Float, ForeignKey, Index, select, delete, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv('PLUMB_DB_PATH', str(ROOT / 'plumb.db')))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False, "timeout": 15}, future=True)

@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _):
    cur=dbapi_connection.cursor(); cur.execute("PRAGMA journal_mode=WAL"); cur.execute("PRAGMA busy_timeout=15000"); cur.execute("PRAGMA foreign_keys=ON"); cur.close()

class Base(DeclarativeBase): pass

class AnalysisRow(Base):
    __tablename__='analyses'
    id: Mapped[str]=mapped_column(String, primary_key=True)
    session_id: Mapped[str]=mapped_column(String, nullable=False, index=True)
    project_name: Mapped[str]=mapped_column(String, nullable=False)
    project_hash: Mapped[str]=mapped_column(String, nullable=False)
    created_at: Mapped[str]=mapped_column(String, nullable=False, index=True)
    payload_json: Mapped[str]=mapped_column(Text, nullable=False)
    requirements=relationship('RequirementRow',cascade='all, delete-orphan',back_populates='analysis')
    evidences=relationship('EvidenceRow',cascade='all, delete-orphan',back_populates='analysis')

class RequirementRow(Base):
    __tablename__='requirements'
    pk: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    analysis_id: Mapped[str]=mapped_column(ForeignKey('analyses.id',ondelete='CASCADE'),nullable=False,index=True)
    requirement_id: Mapped[str]=mapped_column(String,nullable=False)
    title: Mapped[str]=mapped_column(Text,nullable=False)
    description: Mapped[str]=mapped_column(Text,nullable=False)
    status: Mapped[str]=mapped_column(String,nullable=False,index=True)
    depth_percent: Mapped[float]=mapped_column(Float,nullable=False,default=0)
    analysis=relationship('AnalysisRow',back_populates='requirements')
    criteria=relationship('CriterionRow',cascade='all, delete-orphan',back_populates='requirement')
    __table_args__=(Index('uq_requirement_analysis_id','analysis_id','requirement_id',unique=True),)

class CriterionRow(Base):
    __tablename__='acceptance_criteria'
    pk: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    requirement_pk: Mapped[int]=mapped_column(ForeignKey('requirements.pk',ondelete='CASCADE'),nullable=False,index=True)
    criterion_id: Mapped[str]=mapped_column(String,nullable=False,index=True)
    text: Mapped[str]=mapped_column(Text,nullable=False)
    status: Mapped[str]=mapped_column(String,nullable=False,index=True)
    stage: Mapped[str|None]=mapped_column(String,nullable=True)
    requirement=relationship('RequirementRow',back_populates='criteria')

class EvidenceRow(Base):
    __tablename__='evidence_records'
    evidence_id: Mapped[str]=mapped_column(String,primary_key=True)
    analysis_id: Mapped[str]=mapped_column(ForeignKey('analyses.id',ondelete='CASCADE'),nullable=False,index=True)
    kind: Mapped[str]=mapped_column(String,nullable=False,index=True)
    title: Mapped[str]=mapped_column(Text,nullable=False)
    expected: Mapped[str|None]=mapped_column(Text)
    observed: Mapped[str|None]=mapped_column(Text)
    source: Mapped[str|None]=mapped_column(Text)
    line_start: Mapped[int|None]=mapped_column(Integer)
    line_end: Mapped[int|None]=mapped_column(Integer)
    details: Mapped[str]=mapped_column(Text,default='')
    status: Mapped[str|None]=mapped_column(String,index=True)
    raw_json: Mapped[str|None]=mapped_column(Text)
    analysis=relationship('AnalysisRow',back_populates='evidences')
    links=relationship('EvidenceLinkRow',cascade='all, delete-orphan',back_populates='evidence')

class EvidenceLinkRow(Base):
    __tablename__='evidence_links'
    pk: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    evidence_id: Mapped[str]=mapped_column(ForeignKey('evidence_records.evidence_id',ondelete='CASCADE'),nullable=False,index=True)
    requirement_id: Mapped[str|None]=mapped_column(String,index=True)
    criterion_id: Mapped[str|None]=mapped_column(String,index=True)
    relation: Mapped[str]=mapped_column(String,default='SUPPORTS')
    evidence=relationship('EvidenceRow',back_populates='links')

class FindingRow(Base):
    __tablename__='findings'
    pk: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    analysis_id: Mapped[str]=mapped_column(ForeignKey('analyses.id',ondelete='CASCADE'),nullable=False,index=True)
    finding_id: Mapped[str]=mapped_column(String,nullable=False)
    rule: Mapped[str|None]=mapped_column(String,index=True)
    severity: Mapped[str|None]=mapped_column(String,index=True)
    file: Mapped[str|None]=mapped_column(Text)
    line: Mapped[int|None]=mapped_column(Integer)
    payload_json: Mapped[str]=mapped_column(Text,nullable=False)

class CapabilityRow(Base):
    __tablename__='capability_executions'
    pk: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    analysis_id: Mapped[str]=mapped_column(ForeignKey('analyses.id',ondelete='CASCADE'),nullable=False,index=True)
    capability: Mapped[str]=mapped_column(String,nullable=False,index=True)
    status: Mapped[str]=mapped_column(String,nullable=False,index=True)

SessionLocal=sessionmaker(bind=engine,expire_on_commit=False,future=True)

def init_db():
    Base.metadata.create_all(engine)

def _json(v):
    return json.dumps(v,ensure_ascii=False,default=str) if v is not None else None

def save_analysis(session_id: str, analysis: dict):
    """Persist the immutable analysis snapshot plus normalized queryable provenance tables."""
    init_db()
    with SessionLocal.begin() as s:
        old=s.get(AnalysisRow,analysis['analysis_id'])
        if old: s.delete(old); s.flush()
        row=AnalysisRow(id=analysis['analysis_id'],session_id=session_id,project_name=analysis['project_name'],project_hash=analysis['project_hash'],created_at=analysis['created_at'],payload_json=_json(analysis))
        s.add(row); s.flush()
        for r in analysis.get('requirements',[]):
            rr=RequirementRow(analysis_id=row.id,requirement_id=r.get('requirement_id') or r.get('id'),title=r.get('title',''),description=r.get('description',''),status=r.get('status','INCONCLUSIVE'),depth_percent=float(r.get('depth_percent',0) or 0))
            s.add(rr); s.flush()
            for ac in r.get('criteria',[]):
                s.add(CriterionRow(requirement_pk=rr.pk,criterion_id=ac.get('id',''),text=ac.get('text',''),status=ac.get('status','INCONCLUSIVE'),stage=ac.get('stage')))
        for e in analysis.get('evidences',[]):
            er=EvidenceRow(evidence_id=e.get('evidence_id'),analysis_id=row.id,kind=e.get('kind','unknown'),title=e.get('title',''),expected=e.get('expected'),observed=e.get('observed'),source=e.get('source'),line_start=e.get('line_start'),line_end=e.get('line_end'),details=e.get('details',''),status=e.get('status'),raw_json=_json(e.get('raw')))
            s.add(er); s.flush()
            rid=e.get('requirement_id'); cid=e.get('acceptance_criterion_id')
            if rid or cid: s.add(EvidenceLinkRow(evidence_id=er.evidence_id,requirement_id=rid,criterion_id=cid,relation='CONTRADICTS' if e.get('status')=='FAILED' else 'SUPPORTS'))
        for f in analysis.get('findings',[]):
            s.add(FindingRow(analysis_id=row.id,finding_id=f.get('id',''),rule=f.get('rule'),severity=f.get('severity'),file=f.get('file'),line=f.get('line'),payload_json=_json(f)))
        for cap,status in (analysis.get('capability') or {}).items():
            s.add(CapabilityRow(analysis_id=row.id,capability=cap,status=str(status)))

def get_analysis(analysis_id: str, session_id: str | None = None):
    init_db()
    with SessionLocal() as s:
        row=s.get(AnalysisRow,analysis_id)
        if not row or (session_id is not None and row.session_id!=session_id): return None
        return json.loads(row.payload_json)

def list_history(session_id: str):
    init_db()
    with SessionLocal() as s:
        rows=s.scalars(select(AnalysisRow).where(AnalysisRow.session_id==session_id).order_by(AnalysisRow.created_at.desc())).all()
        return [json.loads(r.payload_json) for r in rows]

def delete_history(session_id: str, analysis_id: str):
    init_db()
    with SessionLocal.begin() as s:
        row=s.scalar(select(AnalysisRow).where(AnalysisRow.id==analysis_id,AnalysisRow.session_id==session_id))
        if not row:return 0
        s.delete(row); return 1

def clear_history(session_id: str):
    init_db()
    with SessionLocal.begin() as s:
        rows=s.scalars(select(AnalysisRow).where(AnalysisRow.session_id==session_id)).all(); n=len(rows)
        for r in rows:s.delete(r)
        return n

def relational_health() -> dict:
    """Small diagnostic used by tests/support; does not expose user data."""
    init_db()
    with SessionLocal() as s:
        return {'database':'sqlite+sqlalchemy','analyses':len(s.scalars(select(AnalysisRow.id)).all()),'foreign_keys':True,'wal':True}
