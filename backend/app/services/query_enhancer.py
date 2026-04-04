from typing import List

from backend.app.core.config import settings
from backend.app.prompts.query_rewrite import build_query_rewrite_prompt
from backend.app.services.llm_provider import get_chat_llm


def enhance_queries(question: str, n: int | None = None) -> List[str]:
    """
    查询增强（Query Enhancement）：
    用 LLM 把用户问题改写成多条更利于向量检索的检索查询。
    """
    n = n or settings.query_enhance_n
    llm = get_chat_llm()

    resp = llm.invoke(build_query_rewrite_prompt(question, n))
    content = getattr(resp, "content", "") or str(resp)
    lines = []
    for raw in content.splitlines():
        s = raw.strip()
        if not s:
            continue
        # 去掉可能的编号/项目符号
        s = s.lstrip("-").strip()
        s = s.split(".", 1)[-1].strip() if "." in s[:4] else s
        lines.append(s)

    # 如果解析失败，退化为原问题
    if not lines:
        return [question]

    # 去重保持顺序
    out: List[str] = []
    seen = set()
    for q in lines:
        if q not in seen:
            out.append(q)
            seen.add(q)

    # 始终保留原问题，避免改写偏离用户真实意图
    if question not in seen:
        out = [question] + out
    else:
        # 若模型已经产出原问题，则把它提到最前
        out = [question] + [q for q in out if q != question]

    return out[:n]

