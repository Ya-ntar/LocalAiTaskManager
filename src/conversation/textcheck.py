import re

CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")

def foreign(text):
    return bool(CJK.search(text or ""))