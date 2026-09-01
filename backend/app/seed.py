import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, Customer, KnowledgeChunk, Order, Product
from app.product_knowledge import product_documents, product_embedding_text
from app.security import hash_password
from app.services.embeddings import HashingEmbedder

PRODUCT_NAMES = [
    "Aurora X1 手机", "Aurora X1 Pro 手机", "NovaPad 11 平板", "NovaPad Mini 平板",
    "EchoBuds 3 耳机", "EchoBuds Pro 耳机", "VisionBook 14 笔记本", "VisionBook 16 笔记本",
    "Pulse Watch 5 手表", "Pulse Band 手环", "PixelCam 4K 相机", "PixelCam Mini 相机",
    "AirHub AX6000 路由器", "AirHub Mesh 路由器", "PowerGo 65W 充电器", "PowerGo 100W 充电器",
    "KeyFlow 机械键盘", "ClickPro 无线鼠标", "ViewMax 27 显示器", "ViewMax 32 显示器",
    "SoundBar S2 音箱", "GameDock 扩展坞", "PocketSSD 1TB", "PocketSSD 2TB",
    "HomeEye 摄像头", "PrintGo 打印机", "CleanBot 扫地机", "AirPure 净化器",
    "CookVision 空气炸锅", "SmartLamp Pro 台灯",
]

POLICIES = [
    ("七天无理由退货政策", "售后政策/退货", "商品签收次日起七天内，商品完好且配件齐全可申请无理由退货。"),
    ("质量问题换货政策", "售后政策/换货", "签收十五天内确认质量问题，可申请免费换货并由平台承担运费。"),
    ("数码产品保修政策", "售后政策/保修", "数码产品默认享受十二个月有限保修，人为损坏不在免费保修范围。"),
    ("退款到账说明", "售后政策/退款", "退款审核通过后原路退回，银行卡通常需要三个至七个工作日。"),
    ("隐私与账户安全", "服务规范/隐私", "客服不会索要密码或短信验证码，也不会查询当前客户以外的订单。"),
]


async def ensure_product_knowledge(session: AsyncSession) -> None:
    """幂等补齐或更新每个商品的介绍与参数，兼容已经存在的演示数据库。"""
    products = (await session.scalars(select(Product).order_by(Product.sku))).all()
    sources = [
        source
        for product in products
        for source in (f"商品介绍/{product.sku}", f"详细参数/{product.sku}")
    ]
    existing = (
        await session.scalars(select(KnowledgeChunk).where(KnowledgeChunk.source.in_(sources)))
    ).all()
    by_source = {chunk.source: chunk for chunk in existing}
    embedder = HashingEmbedder()
    for product in products:
        for document in product_documents(product.sku, product.name):
            chunk = by_source.get(document["source"])
            embedding = embedder.embed(product_embedding_text(document))
            if chunk:
                chunk.title = document["title"]
                chunk.category = product.category
                chunk.content = document["content"]
                chunk.embedding = embedding
                chunk.version = "1.0"
            else:
                session.add(
                    KnowledgeChunk(
                        **document,
                        category=product.category,
                        version="1.0",
                        embedding=embedding,
                    )
                )


async def seed_database(session: AsyncSession) -> None:
    """首次启动写入合成业务数据；账号和产品知识分别按需补齐。"""
    count = await session.scalar(select(func.count(Customer.id)))
    if not count:
        customers = [
            Customer(id="CUST-001", name="林晓", tier="gold"),
            Customer(id="CUST-002", name="陈晨", tier="standard"),
            Customer(id="CUST-003", name="周可", tier="standard"),
            Customer(id="AGENT-001", name="演示客服", tier="staff"),
        ]
        session.add_all(customers)
        products = []
        categories = ["手机", "平板", "耳机", "电脑", "智能穿戴", "影像", "网络", "配件", "家电"]
        for index, name in enumerate(PRODUCT_NAMES, start=1):
            products.append(
                Product(
                    id=f"PROD-{index:03d}",
                    sku=f"EC-SKU-{index:03d}",
                    name=name,
                    category=categories[min((index - 1) // 4, len(categories) - 1)],
                    price=float(199 + index * 137),
                    warranty_months=12,
                )
            )
        session.add_all(products)
        await session.flush()
        # 固定随机种子，使订单分布在测试和演示环境中可重复。
        rng = random.Random(20260828)
        now = datetime.now(UTC)
        orders = []
        customer_ids = ["CUST-001", "CUST-002", "CUST-003"]
        for index in range(1, 101):
            delivered = index % 4 != 0
            purchased_at = now - timedelta(days=rng.randint(2, 60))
            delivered_at = now - timedelta(days=3 if index == 1 else rng.randint(1, 25)) if delivered else None
            orders.append(
                Order(
                    id=f"ORDER-{index:03d}",
                    order_no=f"EC202608{index:04d}",
                    customer_id=customer_ids[(index - 1) % 3],
                    product_id=products[(index - 1) % len(products)].id,
                    status="delivered" if delivered else "shipping",
                    amount=products[(index - 1) % len(products)].price,
                    purchased_at=purchased_at,
                    delivered_at=delivered_at,
                    tracking_no=f"SF{202608000000 + index}",
                    carrier="顺丰速运",
                    estimated_delivery=now + timedelta(days=2) if not delivered else delivered_at,
                )
            )
        session.add_all(orders)
        embedder = HashingEmbedder()
        chunks = []
        for title, source, content in POLICIES:
            chunks.append(
                KnowledgeChunk(
                    title=title, source=source, category="policy", content=content,
                    embedding=embedder.embed(title + content),
                )
            )
        for product in products:
            content = (
                f"{product.name} 提供 {product.warranty_months} 个月有限保修。首次使用前请完整充电，"
                "出现无法开机时先检查电源、线缆并长按电源键十秒；仍无法恢复请申请售后检测。"
            )
            chunks.append(
                KnowledgeChunk(
                    title=f"{product.name} 使用与保修说明",
                    source=f"商品手册/{product.sku}",
                    category=product.category,
                    content=content,
                    embedding=embedder.embed(product.name + content),
                )
            )
        session.add_all(chunks)
    account_count = await session.scalar(select(func.count(Account.id)))
    if not account_count:
        session.add_all([
            Account(id="ACCOUNT-CUST-001", username="customer1", password_hash=hash_password("customer123"), role="customer", customer_id="CUST-001"),
            Account(id="ACCOUNT-CUST-002", username="customer2", password_hash=hash_password("customer123"), role="customer", customer_id="CUST-002"),
            Account(id="ACCOUNT-AGENT-001", username="agent", password_hash=hash_password("agent123"), role="agent", customer_id="AGENT-001"),
        ])
    await ensure_product_knowledge(session)
    await session.commit()
