from app.product_knowledge import PRODUCT_KNOWLEDGE, product_documents, product_embedding_text
from app.seed import PRODUCT_NAMES
from app.services.embeddings import HashingEmbedder


def all_documents() -> list[tuple[str, dict[str, str]]]:
    return [
        (f"EC-SKU-{index:03d}", document)
        for index, name in enumerate(PRODUCT_NAMES, start=1)
        for document in product_documents(f"EC-SKU-{index:03d}", name)
    ]


def test_every_product_has_introduction_and_detailed_specs() -> None:
    expected_skus = {f"EC-SKU-{index:03d}" for index in range(1, 31)}
    assert set(PRODUCT_KNOWLEDGE) == expected_skus
    documents = all_documents()
    assert len(documents) == 60
    assert len({document["source"] for _, document in documents}) == 60
    for sku, knowledge in PRODUCT_KNOWLEDGE.items():
        assert len(knowledge.introduction) >= 35, sku
        assert knowledge.specifications.count("；") >= 6, sku
        assert "：" in knowledge.specifications, sku


def test_exact_product_document_is_recalled_in_top_three() -> None:
    embedder = HashingEmbedder()
    indexed = [
        (sku, document["source"], embedder.embed(product_embedding_text(document)))
        for sku, document in all_documents()
    ]
    for index, name in enumerate(PRODUCT_NAMES, start=1):
        sku = f"EC-SKU-{index:03d}"
        for query_suffix, source_prefix in (("产品介绍", "商品介绍"), ("详细参数", "详细参数")):
            query = embedder.embed(name + query_suffix)
            top_three = sorted(
                indexed,
                key=lambda item: sum(left * right for left, right in zip(query, item[2])),
                reverse=True,
            )[:3]
            assert any(
                item_sku == sku and source.startswith(source_prefix)
                for item_sku, source, _ in top_three
            ), (sku, query_suffix, [source for _, source, _ in top_three])
