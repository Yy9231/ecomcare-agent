from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeChunk
from app.services.embeddings import HashingEmbedder


async def search_knowledge(session: AsyncSession, query: str, limit: int = 3) -> list[dict]:
    """执行精确余弦检索，并返回生成回答所需的正文与可追溯来源。"""
    embedding = HashingEmbedder().embed(query)
    # 语料仅 95 条，精确检索不会损失召回，当前无需 HNSW 近似索引。
    statement = (
        select(KnowledgeChunk)
        .order_by(KnowledgeChunk.embedding.cosine_distance(embedding))
        .limit(limit)
    )
    chunks = (await session.scalars(statement)).all()
    return [
        {
            "title": chunk.title,
            "source": chunk.source,
            "content": chunk.content,
            "version": chunk.version,
        }
        for chunk in chunks
    ]
