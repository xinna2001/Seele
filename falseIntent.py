import string

def main(text):
    # 定义包含中文标点符号的字符串
    chinese_punctuation = '！？｡。＂＃＄％＆Ｔ（）＊＋，－／：；＜＝＞＠［＼］＾＿｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘’‛“”„‟…‧﹏.'
    # 合并 ASCII 标点符号和中文标点符号
    all_punctuation = string.punctuation + chinese_punctuation
    translator = str.maketrans('', '', all_punctuation)
    text = text.translate(translator)
    text=text.lower()
    if "执行" in text and "代码" in text or "执行" in text and "程序" in text or "运行" in text and "代码" in text or "运行" in text and "程序" in text:
        text="执行代码"
    elif "下" in text and "ppt" in text :
        text="下载ppt"
    elif "调研" in text and "ppt" in text or "制作" in text and "ppt" in text :
        text="调研ppt"
    elif "初始化" in text:
        text="初始化"
    elif "创建" in text and "工作" in text:
        text="创建工作"
    elif "部署" in text and "项目1" or "部署" in text and "项目一":
        text="部署项目一"
    elif "爬取" in text and "京东" or "抓取" in text and "京东":
        text="京东数据抓取"
    elif "生成" in text and "视频" in text:
        text="生成视频"
    elif "做" in text and "网页" in text or "作" in text and "网页" or "做" in text and "网站" in text or "作" in text and "网站" in text:
        text="生成网页"
    elif "查" in text and "动漫" in text:
        text="查询动漫"
    elif "陪我" in text and "世界" in text:
        text="看看世界"
    elif "陪我" in text and "聊天" in text:
        text="陪我聊天"
    elif "我有github账号" in text:
        text="点星"
    return text

"""
Seele
谁不喜欢能帮你工作又听话的赛博妹妹呢~
谢谢大家使用希儿！本项目使用语音识别+TTS+AI大模型+影刀RPA，
实现的通过语音可以让电脑帮你执行工作流的功能！ 
只要将你的工作教给电脑一遍，它就能学会，并且100%复现，个人认为比有幻觉情况的大模型在执行复制任务时更有优势 
另外，我也希望通过影刀RPA构建开源生态，打破技术壁垒，实现技术平权，让所有人都能体验技术带来的快乐！
"""