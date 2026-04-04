"""文档入库（ETL）切分策略 Agent 的提示词。"""

ETL_AGENT_SYSTEM_PROMPT = """你是文档入库（向量化）前的切分策略专家。
你只能根据用户给出的统计与预览，调用一次 finalize_etl_params，
提交合适的 chunk_size、chunk_overlap、use_single_chunk。
短文、总长明显小于常见检索窗口时优先 use_single_chunk=true。
长文、技术手册、需细粒度检索时用 use_single_chunk=false，并给出合理块长。
overlap 一般取 chunk_size 的 10%～25%，且必须小于 chunk_size。"""


def build_etl_user_prompt(
    file_basename: str,
    ext: str,
    nseg: int,
    total: int,
    default_chunk_size: int,
    default_chunk_overlap: int,
    preview: str,
) -> str:
    return (
        f"待处理文件: {file_basename}\n"
        f"扩展名: {ext}\n"
        f"有效段落数(页/段): {nseg}\n"
        f"总字符数: {total}\n"
        f"默认配置参考: chunk_size={default_chunk_size}, chunk_overlap={default_chunk_overlap}\n"
        f"正文预览(截断): {preview}\n\n"
        "请调用 finalize_etl_params，传入一个 JSON 字符串，例如：\n"
        '{"chunk_size": 400, "chunk_overlap": 80, "use_single_chunk": false}'
    )
