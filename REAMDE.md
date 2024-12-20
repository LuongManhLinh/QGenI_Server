# QGenI_Server

## Giới thiệu

QGenI_Server là một dự án Python tạo Server cho ứng dụng [QGenI](https://github.com/LuongManhLinh/QGenI)

## Yêu cầu hệ thống

- Python 3.6 trở lên
- Các thư viện Python cần thiết (được liệt kê trong `requirements.txt`)

## Cài đặt

1. Clone repository:
    ```bash
    git clone https://github.com/LuongManhLinh/QGenI_Server.git
    ```
2. Chuyển vào thư mục dự án:
    ```bash
    cd QGenI_Server
    ```
3. Cài đặt các thư viện cần thiết:
    ```bash
    pip install -r requirements.txt
    ```

## Sử dụng
1. Config lại những nội dung trong file sau:
    - api.py: 
        - Tại SearchAPI: thay thế __SEARCH_API_KEY và __SEARCH_ENGINE_ID với đường dẫn đến file lưu trữ thông tin cho Google Search API
        - Tại GeminiAPI: thay thế __API_KEY với đường dẫn đến file lưu trữ API Key của Gemini
        - Tại EmailAPI: thay thế __MY_EMAIL và __PASSWORD với đường dẫn đến file lưu trữ tên email và mật khẩu cho việc sử dụng email
    - tfn_server.py: Tại TfnServer, thay thế MODEL_CHECKPOINT và TOKENIZER_CHECKPOINT đến file lưu trữ thông tin về model transformers sử dụng trong tạo bài đọc.

2. Chạy máy chủ:
    ```bash
    python main.py
    ```
3. Kết nối với máy chủ thông qua ứng dụng QGenI
