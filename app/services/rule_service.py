import logging
from typing import List
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.rule import RuleInDB, RuleResponse

logger = logging.getLogger(__name__)


class RuleService:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def create_rule(self, keyword: str, dm_message: str) -> RuleResponse:
        rule_db = RuleInDB.create(keyword=keyword, dm_message=dm_message)
        doc = rule_db.model_dump()
        await self.db.rules.insert_one(doc)
        logger.info(f"Rule created: id={rule_db.rule_id}, keyword='{rule_db.keyword}'")
        return RuleResponse(
            rule_id=rule_db.rule_id,
            keyword=rule_db.keyword,
            dm_message=rule_db.dm_message,
        )

    async def get_all_rules(self) -> List[RuleInDB]:
        cursor = self.db.rules.find()
        rules = []
        async for doc in cursor:
            rules.append(RuleInDB(**doc))
        return rules

    async def match_text(self, text: str) -> List[RuleInDB]:
        if not text:
            return []
        text_upper = text.strip().upper()
        rules = await self.get_all_rules()
        matched = []
        for rule in rules:
            if rule.normalized_keyword in text_upper:
                matched.append(rule)
        return matched
