# 🚀 xiaomiBLQuestionOCR

小米社区 BootLoader（BL）题目 OCR 识别程序  
**基于 [RapidOCR](https://github.com/RapidAI/RapidOCR) 识别引擎**

---

## 📝 简介

本项目用于自动识别小米社区 BL 解锁题目的题干和选项，  
通过摄像头拍摄题目，自动提取内容并匹配答案  

#### 注意：目前仅支持题库内的题目识别，若有答案或题目错误，还是有更好的建议欢迎提issue或者pr！

---

## 🛠️ 使用方法

0. 从release下载打包好的exe程序
1. 运行本程序，首次使用请先点击“更新题库数据”按钮
2. 选择摄像头，调整题目画面至摄像头取景框内
3. 点击“识别”按钮，等待程序自动识别与匹配
4. 查看识别结果，核对后作答 

Ps:若你的电脑没有摄像头或者很模糊，可以使用DroidCam或小米电脑管家（需要小米备用机）将摄像头链接至PC使用

---

## 依赖环境

- Python 3.7+
- PyQt5
- opencv-python
- RapidOCR
- pygrabber
- requests

---

## 关于

- 作者：[@myxuebi](https://github.com/myxuebi)
- OCR识别引擎：[RapidOCR](https://github.com/RapidAI/RapidOCR)
- 本项目完全免费，仅供学习交流使用
