from shiny import App, ui, render, reactive
from dashscope import Application
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
import io
import tempfile

# 应用界面
app_ui = ui.page_fluid(
    ui.panel_title("    审计AI助手"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_text_area(
                "user_input",
                "输入您的问题:",
                placeholder="请在这里输入您想要咨询的问题...",
                rows=5,
                width="100%"
            ),
            ui.input_action_button(
                "submit_btn",
                "提交问题",
                class_="btn-primary",
                width="100%"
            ),
            ui.hr(),
            ui.download_button(
                "download_btn",
                "下载审计报告(PDF)",
                class_="btn-success",
                width="100%"
            ),
            width=400
        ),
        ui.card(
            ui.card_header("AI 回复结果"),
            ui.output_ui("ai_response"),
            ui.output_text_verbatim("loading_status")
        )
    )
)

def wrap_text_lines(text, c, max_width, font_name='Helvetica', font_size=10):
    """
    根据实际 PDF 宽度智能换行
    c: canvas 对象
    max_width: 最大宽度(单位:点)
    """
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph.strip():
            lines.append('')
            continue
        
        # 设置字体以计算宽度
        c.setFont(font_name, font_size)
        
        words = paragraph.split(' ')
        current_line = ''
        
        for word in words:
            test_line = current_line + word + ' ' if current_line else word + ' '
            
            # 计算文本宽度
            text_width = c.stringWidth(test_line, font_name, font_size)
            
            if text_width <= max_width:
                current_line = test_line
            else:
                # 如果当前行不为空,保存当前行
                if current_line:
                    lines.append(current_line.rstrip())
                    current_line = word + ' '
                else:
                    # 单个词太长,需要按字符切分
                    char_line = ''
                    for char in word:
                        test_char_line = char_line + char
                        if c.stringWidth(test_char_line, font_name, font_size) <= max_width:
                            char_line = test_char_line
                        else:
                            if char_line:
                                lines.append(char_line)
                            char_line = char
                    if char_line:
                        current_line = char_line + ' '
        
        # 添加最后一行
        if current_line:
            lines.append(current_line.rstrip())
    
    return lines

def server(input, output, session):
    # 存储 AI 响应的响应式值
    ai_result = reactive.Value("")
    is_loading = reactive.Value(False)
    
    @reactive.Effect
    @reactive.event(input.submit_btn)
    def process_input():
        """处理用户输入并调用 AI API"""
        user_question = input.user_input().strip()
        
        if not user_question:
            ai_result.set("请输入有效的问题。")
            return
        
        is_loading.set(True)
        ai_result.set("正在思考中,请稍候...")
        
        try:
            # 调用通义千问 API
            response = Application.call(
                api_key="sk-f1c91367a7ff4f0c87c4f54f5d696138",
                app_id='61bfdc9175fe4597b4516db2cd70c319',
                prompt=user_question
            )
            
            if response.status_code == 200:
                result_text = response.output.text
                ai_result.set(result_text)
            else:
                ai_result.set(f"API 调用失败,状态码: {response.status_code}")
                
        except Exception as e:
            ai_result.set(f"发生错误: {str(e)}")
        
        finally:
            is_loading.set(False)
    
    @output
    @render.ui
    def ai_response():
        """渲染 AI 响应结果"""
        response_text = ai_result.get()
        
        if response_text and response_text != "正在思考中,请稍候...":
            return ui.div(
                ui.markdown(response_text),
                style="padding: 15px; background-color: #f8f9fa; border-radius: 5px; min-height: 200px;"
            )
        elif response_text == "正在思考中,请稍候...":
            return ui.div(
                ui.tags.i(class_="fa fa-spinner fa-spin"),
                " 正在思考中,请稍候...",
                style="padding: 15px; color: #007bff;"
            )
        else:
            return ui.div(
                "等待您的问题...",
                style="padding: 15px; color: #6c757d; font-style: italic;"
            )
    
    @output
    @render.text
    def loading_status():
        """显示加载状态"""
        if is_loading.get():
            return "状态: 正在处理..."
        else:
            return "状态: 就绪"
    
    @render.download(
        filename=lambda: f"审计报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )
    def download_btn():
        """生成并下载 PDF 格式的审计报告"""
        response_text = ai_result.get()
        user_question = input.user_input().strip()
        
        if not response_text or response_text == "正在思考中,请稍候...":
            response_text = "暂无可下载的内容。"
        if not user_question:
            user_question = "未输入问题"
        
        # 使用 BytesIO 创建 PDF
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # 计算可用宽度(页面宽度 - 左右边距)
        left_margin = 2 * cm
        right_margin = 2 * cm
        content_width = width - left_margin - right_margin
        text_width = content_width - 0.5 * cm  # 为文本内容留出额外边距
        
        # 尝试注册中文字体
        font_registered = False
        font_name = 'Helvetica'
        try:
            font_paths = [
                'C:\\Windows\\Fonts\\simsun.ttc',  # Windows 宋体
                'C:\\Windows\\Fonts\\msyh.ttc',    # Windows 微软雅黑
                'C:\\Windows\\Fonts\\simhei.ttf',  # Windows 黑体
                '/System/Library/Fonts/PingFang.ttc',  # macOS
                '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',  # Linux
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('Chinese', font_path))
                        font_registered = True
                        font_name = 'Chinese'
                        break
                    except:
                        continue
        except:
            pass
        
        # 设置起始位置
        y_position = height - 3 * cm
        
        # 标题
        c.setFont('Helvetica-Bold', 20)
        c.drawString(left_margin, y_position, "AI Audit Report")
        y_position -= 1.2 * cm
        
        # 生成时间
        c.setFont('Helvetica', 10)
        c.drawString(left_margin, y_position, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        y_position -= 1.5 * cm
        
        # 分隔线
        c.line(left_margin, y_position, width - right_margin, y_position)
        y_position -= 1 * cm
        
        # 用户问题标题
        c.setFont('Helvetica-Bold', 12)
        c.drawString(left_margin, y_position, "User Question:")
        y_position -= 0.8 * cm
        
        # 用户问题内容
        question_font_size = 10
        c.setFont(font_name, question_font_size)
        
        question_lines = wrap_text_lines(user_question, c, text_width, font_name, question_font_size)
        for line in question_lines:
            if y_position < 3 * cm:
                c.showPage()
                c.setFont(font_name, question_font_size)
                y_position = height - 3 * cm
            
            try:
                c.drawString(left_margin + 0.5 * cm, y_position, line)
            except:
                # 如果有无法编码的字符,使用替代方案
                safe_line = line.encode('latin-1', 'ignore').decode('latin-1')
                c.drawString(left_margin + 0.5 * cm, y_position, safe_line)
            y_position -= 0.6 * cm
        
        y_position -= 0.5 * cm
        
        # 分隔线
        if y_position < 3 * cm:
            c.showPage()
            y_position = height - 3 * cm
        c.line(left_margin, y_position, width - right_margin, y_position)
        y_position -= 1 * cm
        
        # AI 回复标题
        c.setFont('Helvetica-Bold', 12)
        c.drawString(left_margin, y_position, "AI Response:")
        y_position -= 0.8 * cm
        
        # AI 回复内容
        response_font_size = 10
        c.setFont(font_name, response_font_size)
        
        response_lines = wrap_text_lines(response_text, c, text_width, font_name, response_font_size)
        for line in response_lines:
            if y_position < 3 * cm:
                c.showPage()
                c.setFont(font_name, response_font_size)
                y_position = height - 3 * cm
            
            try:
                c.drawString(left_margin + 0.5 * cm, y_position, line)
            except:
                safe_line = line.encode('latin-1', 'ignore').decode('latin-1')
                c.drawString(left_margin + 0.5 * cm, y_position, safe_line)
            y_position -= 0.6 * cm
        
        # 保存 PDF 到 buffer
        c.save()
        
        # 重置 buffer 位置并以生成器方式返回
        buffer.seek(0)
        
        # 使用 yield 返回字节数据
        yield buffer.read()

# 创建应用

app = App(app_ui, server)
