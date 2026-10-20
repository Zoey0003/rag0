from urllib.parse import urlparse
from uuid import UUID
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"
st.session_state.setdefault("auth_token", None)
# 从旧用户 ID 入口升级时，不沿用未认证的身份。
if not st.session_state.auth_token:
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.session_id = None
    st.session_state.messages = []
    st.session_state.conversations = {}
    st.session_state.pop("session_action", None)
st.set_page_config(page_title="芯知 · 半导体知识助手", page_icon=":material/memory:")

#初始化st的session_state，避免KeyError
# 升级后清除原来的页面会话缓存，数据库记录不受影响。
if st.session_state.get("memory_ui_version") != 1:
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.session_id = None
    st.session_state.messages = []
    st.session_state.conversations = {}
    st.session_state.pop("session_action", None)
    st.session_state.memory_ui_version = 1

def auth_headers():
    """有登录令牌时，在请求头中携带。"""
    token = st.session_state.get("auth_token")
    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}",
    }


def api_request(method, path, **kwargs):
    """调用后端，转换错误响应为便于展示的提示。"""
    # response = requests.request(
    #     method,
    #     f"{API_URL}{path}",
    #     timeout=(10, 30),
    #     **kwargs,
    # )
    headers = dict(kwargs.pop("headers", {}))
    headers.update(auth_headers())

    response = requests.request(
        method,
        f"{API_URL}{path}",
        timeout=(10, 30),
        headers=headers,
        **kwargs,
    )
    handle_auth_expired(response)
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise ValueError(f"HTTP {response.status_code}：{detail}")
    return response.json()


def load_sessions(user_id):
    """从数据库读取用户最近的会话，保持后端返回的排序。"""
    items = api_request(
        "GET",
        "/memory/sessions",
    )
    return {item["session_id"]: item for item in items}

def clear_login():
    """清除当前页面的身份和聊天状态，不删除数据库记录。"""
    st.session_state.auth_token = None
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.session_id = None
    st.session_state.messages = []
    st.session_state.conversations = {}
    st.session_state.pop("session_action", None)
    st.session_state.pop("title_refresh_failed", None)


def handle_auth_expired(response):
    """已登录的请求返回 401 时，清理身份并返回登录入口。"""
    if (
        response.status_code == 401
        and st.session_state.get("auth_token")
    ):
        clear_login()
        st.session_state.auth_notice = "登录已失效，请重新登录。"
        st.rerun()

def activate_user(user):
    """切换用户并加载会话，清除上一用户的界面状态。"""
    # 先请求成功，再替换状态，避免网络失败导致切换一半。
    conversations = load_sessions(user["user_id"])

    st.session_state.user_id = user["user_id"]
    st.session_state.user_name = user["name"]
    st.session_state.session_id = None
    st.session_state.messages = []
    st.session_state.conversations = conversations


def switch_session(session_id):
    """从数据库读取所选会话最近 100 条消息。"""
    messages = api_request(
        "GET",
        f"/memory/sessions/{session_id}/messages",
        params={
            "limit": 100,
        },
    )
    st.session_state.session_id = session_id
    st.session_state.messages = messages


def create_session():
    """使用当前用户创建数据库会话，并选中它。"""
    if not st.session_state.user_id:
        raise ValueError("请先选择或创建用户")

    item = api_request(
        "POST",
        "/memory/sessions",
        json={
            "title": "新对话",
        },
    )
    st.session_state.conversations = {
        item["session_id"]: item,
        **st.session_state.conversations,
    }
    st.session_state.session_id = item["session_id"]
    st.session_state.messages = []


def render_session_menu(session_id):
    """当前会话的操作菜单。"""
    with st.popover("⋮"):
        for label, action in [
            ("重命名", "rename"),
            ("导出", "export"),
            ("删除", "delete"),
        ]:
            if st.button(
                label,
                key=f"session_menu_{action}_{session_id}",
                width="stretch",
            ):
                st.session_state.session_action = {
                    "user_id": st.session_state.user_id,
                    "session_id": session_id,
                    "action": action,
                }
                st.rerun()


def render_session_action():
    """展示菜单中选中的操作。"""
    selection = st.session_state.get("session_action")
    if not selection:
        return

    # 切换用户或会话后，不展示之前的操作。
    if (
        selection["user_id"] != st.session_state.user_id
        or selection["session_id"] != st.session_state.session_id
    ):
        st.session_state.pop("session_action", None)
        return

    actions = {
        "rename": render_session_rename,
        "export": render_session_export,
        "delete": render_session_delete,
    }

    with st.container(border=True):
        actions[selection["action"]]()

        if st.button("关闭操作", key="close_session_action"):
            st.session_state.pop("session_action", None)
            st.rerun()





def render_session_rename():
    """修改当前选中的会话标题。"""
    user_id = st.session_state.user_id
    session_id = st.session_state.session_id

    if not user_id or not session_id:
        return

    conversation = st.session_state.conversations.get(session_id)
    if conversation is None:
        return

    notice_key = f"rename_notice_{user_id}_{session_id}"
    notice = st.session_state.pop(notice_key, None)
    if notice:
        st.success(notice)

    st.caption("重命名当前会话")
    with st.form(f"rename_session_{user_id}_{session_id}"):
        title = st.text_input(
            "会话标题",
            value=conversation.get("title", "新对话"),
            max_chars=200,
        )
        submitted = st.form_submit_button("保存标题")

    if submitted:
        title = title.strip()
        if not title:
            st.warning("会话标题不能为空。")
            return

        try:
            item = api_request(
                "PATCH",
                f"/memory/sessions/{session_id}",
                json={
                    "title": title,
                },
            )

            # 接口成功后再更新本地列表，避免失败时显示错误标题。
            st.session_state.conversations[session_id].update(item)
            st.session_state[notice_key] = "会话标题已更新。"

        except (
            requests.exceptions.RequestException,
            ValueError,
        ) as exc:
            st.error(f"重命名失败：{exc}")
            return

        st.rerun()

def render_session_delete():
    """删除当前会话，提交前要求确认。"""
    user_id = st.session_state.user_id
    session_id = st.session_state.session_id
    if not user_id or not session_id:
        return

    conversation = st.session_state.conversations.get(session_id)
    if conversation is None:
        return

    st.caption("删除当前会话")
    st.write(f"当前会话：{conversation.get('title', '新对话')}")
    st.warning("删除后无法恢复，将删除历史消息和摘要。长期记忆会保留。")
    with st.form(f"delete_session_{user_id}_{session_id}"):
        confirmed = st.checkbox("我确认删除这个会话")
        submitted = st.form_submit_button("删除会话")

    if not submitted:
        return
    if not confirmed:
        st.warning("请先勾选确认。")
        return

    try:
        api_request(
            "DELETE",
            f"/memory/sessions/{session_id}",
            params={},
        )
    except (requests.exceptions.RequestException, ValueError) as exc:
        st.error(f"删除失败：{exc}")
        return

    # 仅在后端成功后清除页面状态。
    st.session_state.conversations.pop(session_id, None)
    st.session_state.session_id = None
    st.session_state.messages = []
    st.session_state[f"session_delete_notice_{user_id}"] = "会话已删除。"
    st.rerun()


def render_session_export():
    """按需生成当前会话的完整 Markdown 下载文件。"""
    user_id = st.session_state.user_id
    session_id = st.session_state.session_id
    if not user_id or not session_id:
        return

    st.caption("导出当前会话")
    st.caption("导出全部已保存的消息和引用来源，不限于页面最近 100 条。")
    if st.button("生成 Markdown 文件", key=f"export_{user_id}_{session_id}"):
        try:
            result = api_request(
                "GET",
                f"/memory/sessions/{session_id}/export",
                params={},
            )
        except (requests.exceptions.RequestException, ValueError) as exc:
            st.error(f"导出失败：{exc}")
            return

        st.download_button(
            "下载会话 Markdown",
            data=result["content"].encode("utf-8-sig"),
            file_name=result["filename"],
            mime="text/markdown; charset=utf-8",
            key=f"download_{user_id}_{session_id}",
            on_click="ignore",
        )
        st.caption("文件为生成时的记录；有新消息后请重新生成。")


def render_memory_panel():
    """展示当前用户的长期记忆，支持手动保存、刷新和删除。"""
    user_id = st.session_state.user_id
    if not user_id:
        return

    # 使用用户 ID 区分表单和提示，避免切换用户后残留内容。
    notice_key = f"memory_notice_{user_id}"

    with st.expander("长期记忆", expanded=False):
        st.caption("回答偏好会用于后续回答；背景信息目前仅保存。")

        notice = st.session_state.pop(notice_key, None)
        if notice:
            st.success(notice)

        with st.form(
            f"memory_form_{user_id}",
            clear_on_submit=True,
        ):
            kind_label = st.selectbox(
                "记忆类型",
                ["回答偏好", "背景信息"],
            )
            content = st.text_area(
                "记忆内容",
                placeholder="例如：技术问题请用通俗语言解释，并举例。",
                max_chars=1000,
            )
            submitted = st.form_submit_button(
                "保存记忆",
                width="stretch",
            )

        if submitted:
            if not content.strip():
                st.warning("请填写记忆内容。")
            else:
                try:
                    api_request(
                        "POST",
                        "/memory/facts",
                        json={
                            "content": content.strip(),
                            "kind": (
                                "preference"
                                if kind_label == "回答偏好"
                                else "fact"
                            ),
                            "source_message_id": None,
                        },
                    )
                    st.success("记忆已保存；相同内容会复用已有记录。")
                except (
                    requests.exceptions.RequestException,
                    ValueError,
                ) as exc:
                    st.error(str(exc))

        # 点击按钮会重新运行页面，下方随即重新请求数据库。
        st.button(
            "刷新记忆",
            key=f"refresh_memories_{user_id}",
            width="stretch",
        )
        st.caption("显示最近 50 条。自动提取完成后，可点击刷新查看。")

        try:
            memories = api_request(
                "GET",
                "/memory/facts",
                params={},
            )
        except (
            requests.exceptions.RequestException,
            ValueError,
        ) as exc:
            st.error(f"记忆列表读取失败：{exc}")
            return

        if not memories:
            st.info("还没有长期记忆。")
            return

        for memory in memories:
            with st.container(border=True):
                label = (
                    "回答偏好"
                    if memory["kind"] == "preference"
                    else "背景信息"
                )
                st.caption(label)
                st.write(memory["content"])

                if st.button(
                    "删除这条记忆",
                    key=f"delete_memory_{user_id}_{memory['memory_id']}",
                ):
                    try:
                        api_request(
                            "DELETE",
                            f"/memory/facts/{memory['memory_id']}",
                            params={},
                        )
                        st.session_state[notice_key] = "记忆已删除。"
                        st.rerun()
                    except (
                        requests.exceptions.RequestException,
                        ValueError,
                    ) as exc:
                        st.error(str(exc))


def render_message(message):
    user = message["role"] == "user"
    avatar = st.session_state.user_avatar if user else ":material/memory:"
    with st.chat_message(message["role"], avatar=avatar):
        st.caption("你" if user else "芯知 · 知识助手")
        if message.get("error"):
            st.error(message["content"])
        else:
            st.markdown(message["content"])
        sources = message.get("sources", [])
        if sources:
            with st.expander(f"参考资料 · {len(sources)} 篇", icon=":material/library_books:"):
                st.caption("本轮参考文档，不代表逐句引用。")
                for i, source in enumerate(sources, 1):
                    title = source.get("title") or source.get("filename") or "未命名资料"
                    st.write(f"[{i}]. {title}")
                    address = source.get("source", "")
                    if source.get("source_type") == "web" and urlparse(address).scheme in {"http", "https"}:
                        st.link_button("查看网页", address, icon=":material/open_in_new:")
                    elif source.get("filename"):
                        st.caption(source["filename"])
                    if address:
                        st.text(address)

with st.sidebar:
    st.title(":material/memory: 芯知")
    st.caption("半导体知识助手")

    # with st.expander("用户入口", expanded=not bool(st.session_state.user_id)):
    #     with st.form("create_user_form"):
    #         user_name = st.text_input("新用户名称", max_chars=100)
    #         create_user_submitted = st.form_submit_button("创建用户")
    #     if create_user_submitted:
    #         try:
    #             user = api_request("POST", "/memory/users", json={"name": user_name.strip()})
    #             activate_user(user)
    #             st.rerun()
    #         except (requests.exceptions.RequestException, ValueError) as exc:
    #             st.error(str(exc))

    #     with st.form("restore_user_form"):
    #         existing_user_id = st.text_input("已有用户 ID")
    #         restore_user_submitted = st.form_submit_button("使用已有用户")
    #     if restore_user_submitted:
    #         try:
    #             user_id = str(UUID(existing_user_id.strip()))
    #             user = api_request("GET", f"/memory/users/{user_id}")
    #             activate_user(user)
    #             st.rerun()
    #         except (requests.exceptions.RequestException, ValueError) as exc:
    #             st.error(str(exc))
    auth_notice = st.session_state.pop("auth_notice", None)
    if auth_notice:
        st.info(auth_notice)
    if not st.session_state.get("auth_token"):
        login_tab, register_tab = st.tabs(["登录", "注册"])

        with login_tab:
            with st.form("login_form", clear_on_submit=True):
                username = st.text_input(
                    "账号",
                    max_chars=64,
                )
                password = st.text_input(
                    "密码",
                    type="password",
                    max_chars=128,
                )
                login_submitted = st.form_submit_button("登录")

            if login_submitted:
                try:
                    result = api_request(
                        "POST",
                        "/auth/login",
                        json={
                            "username": username,
                            "password": password,
                        },
                    )

                    # 先保存令牌，加载会话时才能通过认证。
                    st.session_state.auth_token = result["access_token"]
                    activate_user(result["user"])

                except (
                    requests.exceptions.RequestException,
                    ValueError,
                    KeyError,
                ) as exc:
                    clear_login()
                    st.error(f"登录未完成：{exc}")
                else:
                    st.rerun()

        with register_tab:
            st.caption(
                "账号使用 3～64 位英文字母、数字或下划线；"
                "密码为 8～128 位。"
            )

            with st.form("register_form", clear_on_submit=True):
                new_username = st.text_input(
                    "注册账号",
                    max_chars=64,
                )
                display_name = st.text_input(
                    "显示名称",
                    max_chars=100,
                )
                new_password = st.text_input(
                    "设置密码",
                    type="password",
                    max_chars=128,
                )
                confirm_password = st.text_input(
                    "确认密码",
                    type="password",
                    max_chars=128,
                )
                register_submitted = st.form_submit_button("注册")

            if register_submitted:
                if new_password != confirm_password:
                    st.error("两次输入的密码不一致。")
                else:
                    try:
                        api_request(
                            "POST",
                            "/auth/register",
                            json={
                                "username": new_username,
                                "name": display_name,
                                "password": new_password,
                            },
                        )
                    except (
                        requests.exceptions.RequestException,
                        ValueError,
                    ) as exc:
                        st.error(f"注册失败：{exc}")
                    else:
                        st.success("注册成功，请切换到登录页签登录。")

    else:
        if st.button("退出登录", width="stretch"):
            try:
                api_request("POST", "/auth/logout")
            except (
                requests.exceptions.RequestException,
                ValueError,
            ) as exc:
                st.error(f"退出失败，请重试：{exc}")
            else:
                clear_login()
                st.rerun()

    if st.session_state.user_id:
        st.caption(f"当前用户：{st.session_state.user_name}")
        st.caption("会话与记忆关联当前登录账号。")

        if st.button(
            "新建对话",
            icon=":material/add_comment:",
            width="stretch",
        ):
            try:
                create_session()
                st.rerun()
            except (requests.exceptions.RequestException, ValueError) as exc:
                st.error(str(exc))

        if st.button("刷新会话列表", width="stretch"):
            try:
                st.session_state.conversations = load_sessions(
                    st.session_state.user_id
                )
                st.rerun()
            except (requests.exceptions.RequestException, ValueError) as exc:
                st.error(str(exc))

        st.subheader("会话记录")
        if st.session_state.get("title_refresh_failed"):
            st.caption("会话列表刷新失败，请点击“刷新会话列表”。")

        # for session_id, conversation in st.session_state.conversations.items():
        #     title = conversation.get("title") or "新对话"
        #     label = title[:22] + ("…" if len(title) > 22 else "")

        #     if st.button(
        #         label,
        #         key=f"conversation_{session_id}",
        #         help=title,
        #         icon=":material/chat_bubble:",
        #         type=(
        #             "primary"
        #             if session_id == st.session_state.session_id
        #             else "secondary"
        #         ),
        #         width="stretch",
        #     ):
        #         try:
        #             switch_session(session_id)
        #             st.rerun()
        #         except (requests.exceptions.RequestException, ValueError) as exc:
        #             st.error(str(exc))
        for session_id, conversation in st.session_state.conversations.items():
            title = conversation.get("title") or "新对话"
            label = title[:22] + ("…" if len(title) > 22 else "")
            is_current = session_id == st.session_state.session_id

            title_column, menu_column = st.columns(
                [5, 1],
                vertical_alignment="center",
            )

            with title_column:
                if st.button(
                    label,
                    key=f"conversation_{session_id}",
                    help=title,
                    icon=":material/chat_bubble:",
                    type="primary" if is_current else "secondary",
                    width="stretch",
                ):
                    try:
                        switch_session(session_id)
                        st.session_state.pop("session_action", None)
                        st.rerun()
                    except (
                        requests.exceptions.RequestException,
                        ValueError,
                    ) as exc:
                        st.error(str(exc))

            with menu_column:
                if is_current:
                    render_session_menu(session_id)
    if st.session_state.user_id:
        delete_notice = st.session_state.pop(
            f"session_delete_notice_{st.session_state.user_id}", None
        )
        if delete_notice:
            st.success(delete_notice)
    render_session_action()
    render_memory_panel()
    st.selectbox(
        "选择你的头像",
        ["🎈","🎆"],
        key="user_avatar",
    )
    st.caption("成功问答保存在数据库中，打开会话显示最近 100 条消息。")
    with st.expander("上传知识资料", icon=":material/upload_file:"):
        st.caption("支持 UTF-8 Markdown，最大 5 MiB。资料仅用于你的知识库；同名上传会更新已有文档。")
        with st.form("upload_document_form", clear_on_submit=True):
            uploaded_file = st.file_uploader(
                "选择 Markdown 文件",
                type=["md"],
                max_upload_size=5,
            )
            upload_submitted = st.form_submit_button(
                "上传或更新",
                icon=":material/upload:",
                width="stretch",
            )

        if upload_submitted:
            if uploaded_file is None:
                st.warning("请先选择文件。")
            else:
                try:
                    with st.spinner("正在解析资料并写入知识库……"):
                        response = requests.post(
                            f"{API_URL}/documents/upload",
                            headers=auth_headers(),
                            files={
                                "file": (
                                    uploaded_file.name,
                                    uploaded_file.getvalue(),
                                    "text/markdown",
                                )
                            },
                            timeout=(10, 300),
                        )
                        handle_auth_expired(response)
                        response.raise_for_status()
                        result = response.json()

                    if result.get("status") == "skipped":
                        st.info("文件内容未变化，已跳过重复入库。")
                    elif result.get("status") == "updated":
                        st.success(
                            f"入库完成：{result['filename']}，"
                            f"{result['chunk_count']} 个文档块。"
                        )
                    else:
                        st.error("接口返回了未知的导入状态。")

                except requests.exceptions.Timeout:
                    st.error(
                        "等待超时，后台可能仍在处理。"
                        "稍后可再次上传同一文件确认结果。"
                    )
                except requests.exceptions.ConnectionError:
                    st.error("无法连接上传服务，请确认 API 已启动。")
                except requests.exceptions.HTTPError as exc:
                    try:
                        detail = exc.response.json().get("detail", "上传失败")
                    except ValueError:
                        detail = "上传失败，请查看 API 终端。"
                    st.error(str(detail))
                except (requests.exceptions.RequestException, ValueError, KeyError):
                    st.error("未能获取有效的上传结果，请查看 API 终端。")

    if st.session_state.get("auth_token"):
        with st.expander("删除知识资料", icon=":material/delete:"):
            try:
                delete_notice = st.session_state.pop("document_delete_notice", None)
                if delete_notice:
                    st.success(delete_notice)
                document_items = api_request("GET", "/documents")
                if not document_items:
                    st.caption("暂无个人资料，可先上传 Markdown。")
                else:
                    document_map = {item["document_id"]: item for item in document_items}
                    selected_document = st.selectbox(
                        "选择要删除的文档",
                        options=list(document_map),
                        format_func=lambda key: document_map[key]["filename"] + (
                            "（删除未完成，可重试）" if document_map[key]["status"] == "deleting" else ""
                        ),
                        key=f"delete_document_{st.session_state.user_id}",
                    )
                    confirmed = st.checkbox(
                        "确认删除所选文档及其知识库内容",
                        key=f"confirm_document_delete_{selected_document}",
                    )
                    if st.button("删除所选文档", disabled=not confirmed, width="stretch"):
                        api_request("DELETE", f"/documents/{selected_document}")
                        st.session_state.document_delete_notice = "文档已删除。"
                        st.rerun()
            except (requests.exceptions.RequestException, ValueError, KeyError):
                st.error("文档操作未完成，请检查服务后重试。")

# if not st.session_state.user_id:
#     st.info("请先在侧边栏创建用户，或填写已有用户 ID。")
#     st.stop()
if not st.session_state.get("auth_token"):
    st.info("请先在侧边栏注册或登录。")
    st.stop()

if not st.session_state.session_id:
    st.info("请新建对话，或在侧边栏选择已有会话。")
    st.stop()



st.title("让半导体知识，更容易理解")
st.caption("芯知 / 知识库问答")
suggestion = None
if not st.session_state.messages:
    with st.container(border=True):
        st.subheader("你好，今天想了解什么？", icon=":material/waving_hand:")
        st.write("从工艺原理到技术对比，输入问题，芯知帮你查找资料并整理答案。")
    st.caption("从一个问题开始")
    examples = [
        ("封装成本", "晶圆级封装为什么能降低成本？", ":material/payments:"),
        ("刻蚀工艺", "高深宽比等离子体刻蚀需要控制哪些因素？", ":material/science:"),
    ]
    for column, (label, question, icon) in zip(st.columns(2), examples):
        with column:
            if st.button(label, icon=icon, width="stretch"):
                suggestion = question

for message in st.session_state.messages:
    render_message(message)

question = st.chat_input("输入问题，例如：晶圆级封装有哪些优势？", max_chars=2000, submit_mode="disable")
question = (question or suggestion or "").strip()
if question:
    user_message = {"role": "user", "content": question}
    # history = [
    # {"role": message["role"], "content": message["content"]}
    # for message in st.session_state.messages
    # if not message.get("error")
    # ][-10:]
    st.session_state.messages.append(user_message)
    render_message(user_message)
    try:
        with st.spinner("正在查找资料并整理回答……"):
            # response = requests.post(f"{API_URL}/ask", json={"question": question,"history": history}, timeout=(10, 180))
            response = requests.post(
                f"{API_URL}/ask",
                headers=auth_headers(),
                json={
                    "session_id": st.session_state.session_id,
                    "question": question,
                },
                timeout=(10, 180),
            )
            handle_auth_expired(response)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict) or not isinstance(result.get("answer"), str):
                raise ValueError("返回格式不正确")
            sources = result.get("sources", [])
            if not isinstance(sources, list) or not all(isinstance(s, dict) for s in sources):
                raise ValueError("来源格式不正确")
        message = {"role": "assistant", "content": result["answer"], "sources": sources}
    except requests.exceptions.Timeout:
        message = {"role": "assistant", "content": "等待超时，请稍后再试。", "error": True}
    except requests.exceptions.ConnectionError:
        message = {"role": "assistant", "content": "无法连接问答服务，请确认 API 已启动。", "error": True}
    except requests.exceptions.HTTPError as exc:
        if exc.response.status_code == 404:
            content = "当前会话已失效，请点击“新建对话”后重新提问。"
        else:
            content = (
                f"问答服务返回 HTTP {exc.response.status_code}，"
                "请查看 API 终端。"
            )
        message = {
            "role": "assistant",
            "content": content,
            "error": True,
        }
    except (ValueError, requests.exceptions.RequestException):
        message = {"role": "assistant", "content": "未能获取有效回答，请稍后重试。", "error": True}
    # st.session_state.messages.append(message)
    # st.rerun()
    st.session_state.messages.append(message)

    # 单独处理列表刷新失败，避免把成功回答显示成问答失败。
    if not message.get("error"):
        try:
            st.session_state.conversations = load_sessions(
                st.session_state.user_id
            )
            st.session_state.title_refresh_failed = False
        except (requests.exceptions.RequestException, ValueError):
            st.session_state.title_refresh_failed = True

    st.rerun()
