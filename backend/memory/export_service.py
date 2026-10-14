"""会话导出：将已保存的聊天记录转换为 Markdown。"""

from uuid import UUID

from sqlalchemy.orm import Session

from memory import repository


def export_session_markdown(
    db: Session,
    user_id: UUID,
    session_id: UUID,
) -> dict[str, str]:
    """导出完整原始消息和来源，不包含长期记忆。"""
    chat_session = repository.get_session(db, user_id, session_id)
    messages = repository.list_all_messages(db, user_id, session_id)
    title = " ".join(chat_session.title.split()) or "新对话"
    parts = [
        f"# {title}",
        f"会话 ID：{chat_session.id}",
        f"创建时间：{chat_session.created_at.isoformat()}",
    ]
    if not messages:
        parts.append("暂无已保存的消息。")

    for message in messages:
        role = "用户" if message.role == "user" else "助手"
        parts.extend([
            "---",
            f"## {role}",
            f"时间：{message.created_at.isoformat()} · 状态：{message.status}",
            message.content,
        ])
        if message.sources:
            parts.append("### 参考资料")
            for index, source in enumerate(message.sources, 1):
                source_title = (
                    source.get("title") or source.get("filename") or "未命名资料"
                )
                parts.append(f"[{index}] {source_title}")
                if source.get("source"):
                    parts.append(f"来源：{source['source']}")

    return {
        "filename": f"conversation-{session_id}.md",
        "content": "\n\n".join(parts) + "\n",
    }
