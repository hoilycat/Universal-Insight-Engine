from sqlalchemy import event
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from app.database import DesignHistory, CoffeeLog
from app.core.ingestion import ingest_design_from_dict
from app.core.ingestion_coffee import ingest_coffee_from_dict

# -----------------------------------------------
# SQLAlchemy Event Listener
# DB 커밋 직후 자동으로 감지
# -----------------------------------------------

def register_auto_ingest(session: Session, background_tasks: BackgroundTasks):
    """
    세션에 이벤트 리스너 등록.
    커밋 발생 시 새 레코드 자동 감지 → 백그라운드 ingestion 실행
    """

    @event.listens_for(session, "after_flush")
    def after_flush(session, flush_context):
        for obj in session.new:
            if isinstance(obj, DesignHistory):
                # ✅ 세션 닫히기 전에 dict로 복사
                data = {
                    "id": obj.id,
                    "description": obj.description,
                    "brightness": obj.brightness,
                    "complexity": obj.complexity,
                    "created_at": str(obj.created_at),
                }
                background_tasks.add_task(ingest_design_from_dict, data)

            elif isinstance(obj, CoffeeLog):
                data = {
                    "id": obj.id,
                    "caffeine_mg": obj.caffeine_mg,
                    "drink_type": obj.drink_type,
                    "body_reaction": obj.body_reaction,
                    "created_at": str(obj.created_at),
                }
                background_tasks.add_task(ingest_coffee_from_dict, data)