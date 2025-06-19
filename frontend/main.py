import streamlit as st
import requests
import time
from pdf2image import convert_from_path
import os
from PIL import Image

BASE_URL = "https://1aef-34-9-69-239.ngrok-free.app"
API_URL = f"{BASE_URL}/chat"
METADATA_API_URL = f"{BASE_URL}/metadata"

def login_form():
    if os.path.exists("company_logo.png"):
        st.image("company_logo.png", width=500)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>ĐĂNG NHẬP</h2>", unsafe_allow_html=True)

    username = st.text_input("Số định danh cá nhân")
    password = st.text_input("Mật khẩu", type="password")
    login_btn = st.button("Đăng nhập")

    if login_btn:
        if username == "0986226372" and password == "123456":
            st.session_state.logged_in = True
            st.session_state.page = "chat"
        else:
            st.error("Sai thông tin đăng nhập")

def setup_sidebar():
    st.sidebar.title("PBL7 Chat")

    if st.sidebar.button("🗑 Xóa lịch sử chat"):
        st.session_state.messages = []

    data_source = st.sidebar.radio("Select data source", ("Từ thiết bị này", "URL"), index=0)
    if data_source == "Từ thiết bị này":
        uploaded_file = st.sidebar.file_uploader("Chọn tệp tin", type=["txt", "pdf"])
        if uploaded_file is not None:
            st.session_state["uploaded_file"] = uploaded_file
            st.session_state["url"] = None  
    else:
        url = st.sidebar.text_input("Nhập URL")
        if url:
            st.session_state["url"] = url
            st.session_state["uploaded_file"] = None  

    st.session_state["data_source"] = data_source

    # st.sidebar.markdown(
    #     """
    #     <div style="
    #         background-color:#f0f2f6;
    #         padding: 10px;
    #         border-radius: 10px;
    #         border: 1px solid #d3d3d3;
    #     ">
    #         <h4 style="margin-bottom:5px;">👨‍🎓 Sinh viên thực hiện</h4>
    #         <ul style="margin-top: 0;">
    #             <li><b>Trần Đình Thắng</b></li>
    #             <li><b>Lê Quốc Vinh</b></li>
    #         </ul>
    #         <h4 style="margin-bottom:5px;">👨‍🏫 Giảng viên hướng dẫn</h4>
    #         <p style="margin-top: 0;"><b>PGS.TS Nguyễn Tấn Khôi</b></p>
    #     </div>
    #     """,
    #     unsafe_allow_html=True
    # )


def main():
    st.set_page_config(page_title="PBL7 Chat")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_form() 
        return  
    
    st.image("company_logo.png", width=1000)
    st.subheader("Xin chào, tôi có thể giúp gì cho bạn?")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Nhập câu hỏi của bạn"):
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            try:
                with requests.get(API_URL, params={"q": prompt}, stream=True, timeout=60) as response:
                    if response.status_code == 200:
                        for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
                            if chunk:
                                full_response += chunk
                                message_placeholder.markdown(full_response + "▌")
                                time.sleep(0.03)
                        message_placeholder.markdown(full_response)
                    else:
                        full_response = f"Lỗi: {response.status_code}"
                        message_placeholder.markdown(full_response)
            except requests.exceptions.RequestException as e:
                full_response = f"Lỗi khi kết nối API: {str(e)}"
                message_placeholder.markdown(full_response)

            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response,
            })

            metadata_response = requests.get(METADATA_API_URL, params={"q": prompt})
            selected_pages = metadata_response.json().get("pages", [])
            selected_pages = sorted(set(page + 1 for page in selected_pages))

            pdf_path = "static/thu_tuc_hanh_chinh.pdf"
            images = []

            for page_num in selected_pages:
                img = convert_from_path(pdf_path, dpi=150, first_page=page_num, last_page=page_num)[0]
                images.append((page_num, img)) 

            with st.expander("🔍 Xem trích dẫn"):
                st.markdown(
                    """
                    <style>
                    .scroll-container {
                        max-height: 600px;
                        overflow-y: auto;
                        padding-right: 10px;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )

                with st.container():
                    st.markdown('<div class="scroll-container">', unsafe_allow_html=True)
                    for page_num, img in images:
                        st.image(img, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True)

    setup_sidebar()


if __name__ == "__main__":
    main()
