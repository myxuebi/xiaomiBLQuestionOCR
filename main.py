import json
import sys
import cv2
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QComboBox, QDialog, QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt, QUrl
from PyQt5.QtGui import QImage, QPixmap, QColor, QDesktopServices
from pygrabber.dshow_graph import FilterGraph
from rapidocr import RapidOCR
import difflib
import os
engine = RapidOCR()

def fuzzy_match(text, candidates, threshold=0.6):
    best_candidate = None
    highest = 0
    for cand in candidates:
        ratio = difflib.SequenceMatcher(None, text, cand).ratio()
        if ratio > highest:
            highest = ratio
            best_candidate = cand
    return best_candidate if highest >= threshold else None, highest

def extract_question_and_options_from_list(ocr_text, question_json_list, option_threshold=0.5, question_threshold=0.5):
    best_question = None
    best_score = 0
    best_json = None
    for qjson in question_json_list:
        q = qjson['question']
        score = difflib.SequenceMatcher(None, ocr_text, q).ratio()
        if score > best_score:
            best_score = score
            best_question = q
            best_json = qjson
    if best_score < question_threshold:
        for qjson in question_json_list:
            options = qjson.get('options', [])
            for opt in options:
                score = difflib.SequenceMatcher(None, ocr_text, opt).ratio()
                if score > best_score:
                    best_score = score
                    best_question = qjson['question']
                    best_json = qjson
    if not best_json:
        return None, None, None
    if best_json.get('type') == 'choice':
        matched_options = best_json['options']
    else:
        matched_options = None
    answer = best_json.get('answer', None)
    return best_json['question'], matched_options, answer

def scan_cameras():
    graph = FilterGraph()
    devices = graph.get_input_devices()
    return [(name, idx) for idx, name in enumerate(devices)]

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setModal(True)
        label = QLabel()
        label.setTextFormat(Qt.RichText)
        label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        label.setOpenExternalLinks(False)
        label.setText(
            '作者：<a href="https://github.com/myxuebi">@myxuebi</a><br>'
            'OCR识别：<a href="https://github.com/RapidAI/RapidOCR">RapidOCR</a>'
        )
        label.linkActivated.connect(self.open_link)
        vbox = QVBoxLayout()
        vbox.addWidget(label)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        vbox.addWidget(button_box)
        self.setLayout(vbox)

    def open_link(self, url):
        QDesktopServices.openUrl(QUrl(url))

class CameraApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("小米社区BL答题OCR题目识别程序")
        self.resize(650, 550)

        layout = QVBoxLayout()

        self.hint_label = QLabel("首次使用请先点击“更新题库数据”按钮，否则无法获取题目信息！！！")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setStyleSheet("QLabel { color : red; font-weight: bold; }")
        layout.addWidget(self.hint_label)

        self.update_btn = QPushButton("更新题库数据")
        self.update_btn.clicked.connect(self.update_question_bank)
        layout.addWidget(self.update_btn)

        self.about_btn = QPushButton("关于")
        self.about_btn.clicked.connect(self.show_about)
        layout.addWidget(self.about_btn)

        self.combo = QComboBox()
        self.cams = scan_cameras()
        for name, idx in self.cams:
            self.combo.addItem(name, idx)
        self.combo.currentIndexChanged.connect(self.change_camera)
        layout.addWidget(self.combo)

        self.video_label = QLabel("摄像头预览")
        self.video_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.video_label, stretch=1)

        self.recognize_btn = QPushButton("识别")
        self.recognize_btn.clicked.connect(self.save_and_recognize)
        layout.addWidget(self.recognize_btn)

        self.result_label = QLabel("请注意！！！题目判断词和选项顺序可能会有区别，请核对后再答题！！！本程序完全免费！！！\n作者@myxuebi")
        self.result_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("QLabel { background-color : #eee; padding: 8px; border: 1px solid #ccc; }")
        layout.addWidget(self.result_label)

        self.setLayout(layout)

        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.display_frame)
        self.frame = None

        if self.cams:
            self.open_camera(self.cams[0][1])

    def show_about(self):
        dialog = AboutDialog(self)
        dialog.exec_()

    def update_question_bank(self):
        url = "https://shell.myxuebi.top/xiaomibl/question.json"
        save_path = os.path.join(os.getcwd(), "question.json")
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(resp.text)
            self.hint_label.setText("题库数据已成功更新！")
            self.hint_label.setStyleSheet("QLabel { color : green; font-weight: bold; }")
        except Exception as e:
            self.hint_label.setText("题库数据更新失败：" + str(e))
            self.hint_label.setStyleSheet("QLabel { color : red; font-weight: bold; }")

    def open_camera(self, idx):
        if self.cap is not None:
            self.cap.release()
        self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        self.timer.start(30)

    def change_camera(self, index):
        cam_idx = self.combo.itemData(index)
        self.open_camera(cam_idx)

    def display_frame(self):
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.frame = frame
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb.shape
                bytes_per_line = ch * w
                image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pix = QPixmap.fromImage(image).scaled(
                    self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio
                )
                self.video_label.setPixmap(pix)

    def save_and_recognize(self):
        if self.frame is not None:
            self.recognize_callback(self.frame)

    def recognize_callback(self, frame):
        cv2.imwrite('res.png', frame)
        result = engine('res.png')
        if result.txts is not None:
            result_txt = ""
            for i in result.txts:
                result_txt += i
            question_path = os.path.join(os.getcwd(), "question.json")
            if not os.path.isfile(question_path):
                QMessageBox.critical(None, "错误", f"未找到题库文件,请先点击更新题库后再试！")
            else:
                with open(os.path.join(os.getcwd(), "question.json"), "r", encoding="utf-8") as f:
                    question = json.loads(f.read())
                q, opts, ans = extract_question_and_options_from_list(result_txt, question)
                option_lines = []
                option_index_map = {}
                if opts is not None:
                    for i, item in enumerate(opts):
                        option_lines.append(f"{i + 1}. {item}")
                        option_index_map[item] = i + 1

                answer_lines = []
                if ans is not None:
                    for item in ans:
                        if opts is not None and item in option_index_map:
                            idx = option_index_map[item]
                            answer_lines.append(f"{idx}. {item}")
                        else:
                            answer_lines.append(f"{ans.index(item) + 1}. {item}")

                self.result_label.setText(
                    "识别结果：\n请注意！！！题目判断词和选项顺序可能会有区别，请核对后再答题！！！本程序完全免费！！！\n作者@myxuebi"
                    + "\n\n题目：" + q
                    + "\n\n选项：" + ("" if opts is None else "\n".join(option_lines))
                    + "\n\n答案：" + ("" if ans is None else "\n".join(answer_lines))
                )
        else:
            self.result_label.setText("未识别到题目信息")

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        self.timer.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CameraApp()
    window.show()
    sys.exit(app.exec_())