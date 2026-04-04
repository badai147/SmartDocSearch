"""ETL：由 Agent 提交切分参数的工具。"""

import json
from typing import Any, Dict

from langchain_core.tools import tool


def create_finalize_etl_params_tool(holder: Dict[str, Any]):
    """
    holder 由调用方传入；工具成功解析后写入 chunk_size / chunk_overlap / use_single_chunk。
    """

    @tool
    def finalize_etl_params(params_json: str) -> str:
        """
        提交最终切分参数。params_json 为 JSON 字符串，键：
        chunk_size（整数）、chunk_overlap（整数）、use_single_chunk（布尔）。
        use_single_chunk 为 true 时整份合并为一条向量，适合短文或需整体语义的文档。
        """
        try:
            raw = json.loads(params_json)
        except json.JSONDecodeError as e:
            return f"JSON 无效: {e}，请重试。"
        try:
            cs = int(raw["chunk_size"])
            co = int(raw["chunk_overlap"])
            single = bool(raw["use_single_chunk"])
        except (KeyError, TypeError, ValueError) as e:
            return f"缺少或类型错误: {e}，需要 chunk_size、chunk_overlap、use_single_chunk。"

        if cs < 50 or cs > 32000:
            return "chunk_size 建议在 50～32000 之间。"
        if co < 0 or co >= cs:
            return "chunk_overlap 必须满足 0 <= overlap < chunk_size。"

        holder.clear()
        holder["chunk_size"] = cs
        holder["chunk_overlap"] = co
        holder["use_single_chunk"] = single
        return "参数已记录，无需再调用工具。"

    return finalize_etl_params
