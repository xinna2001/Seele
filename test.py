from rpa_service import is_shadowbot_running


if __name__ == "__main__":
    print("运行" if is_shadowbot_running() else "没有运行")
