import hashlib
import math


class HashingEmbedder:
    """无密钥、可重复的离线向量器，用于演示和稳定测试，不等同于语义模型。"""

    dimensions = 1536

    def embed(self, text: str) -> list[float]:
        # 中文相邻二元字符比整句哈希保留更多局部词项信息。
        normalized = "".join(text.lower().split())
        features = [normalized[index : index + 2] for index in range(max(1, len(normalized) - 1))]
        vector = [0.0] * self.dimensions
        for feature in features:
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        # 归一化后可直接使用 pgvector 的余弦距离比较相似度。
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
