import subprocess

def run_tasklist():
    # 使用 cmd 执行 tasklist 命令
    cmd = 'tasklist /fi "imagename eq ShadowBotBrowser*"'
    # 使用 subprocess 执行命令
    result = subprocess.run(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    # 获取标准输出和错误输出
    stdout = result.stdout
    return stdout


# 调用函数并打印结果
stdout = run_tasklist()

