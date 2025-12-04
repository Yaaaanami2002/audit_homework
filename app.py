from shiny import App, ui, render, reactive
from dashscope import Application
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
import io

# 应用界面
app_ui = ui.page_fluid(
    # 自定义 CSS 样式
    ui.tags.head(
        ui.tags.style("""
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');
            
            body {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                font-family: 'Noto Sans SC', sans-serif;
                min-height: 100vh;
            }
            
            .app-title {
                text-align: center;
                font-size: 2.8rem;
                font-weight: 700;
                color: white;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
                padding: 2rem 0 1.5rem 0;
                margin: 0;
                letter-spacing: 2px;
            }
            
            .app-subtitle {
                text-align: center;
                font-size: 1rem;
                color: rgba(255,255,255,0.9);
                margin-bottom: 2rem;
                font-weight: 300;
            }
            
            .main-container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 0 20px;
            }
            
            .sidebar {
                background: white;
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                height: fit-content;
            }
            
            .sidebar label {
                font-weight: 600;
                color: #333;
                font-size: 1.05rem;
                margin-bottom: 8px;
            }
            
            textarea {
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                padding: 12px;
                font-size: 0.95rem;
                transition: all 0.3s ease;
            }
            
            textarea:focus {
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
                outline: none;
            }
            
            .btn-primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 1.05rem;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102,126,234,0.4);
            }
            
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102,126,234,0.6);
            }
            
            .btn-success {
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                border: none;
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 1.05rem;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(17,153,142,0.4);
            }
            
            .btn-success:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(17,153,142,0.6);
            }
            
            .card {
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                border: none;
                overflow: hidden;
            }
            
            .card-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px 25px;
                font-size: 1.3rem;
                font-weight: 600;
                border: none;
            }
            
            .response-box {
                padding: 25px;
                background-color: #f8f9fa;
                border-radius: 12px;
                min-height: 250px;
                margin: 20px;
                font-size: 1rem;
                line-height: 1.7;
            }
            
            .status-indicator {
                padding: 15px 20px;
                margin: 0 20px 20px 20px;
                background: #e3f2fd;
                border-radius: 10px;
                border-left: 4px solid #2196f3;
                font-weight: 500;
                color: #1565c0;
            }
            
            .loading-text {
                color: #667eea;
                font-weight: 500;
            }
            
            .waiting-text {
                color: #9e9e9e;
                font-style: italic;
            }
            
            hr {
                border: none;
                height: 1px;
                background: linear-gradient(to right, transparent, #e0e0e0, transparent);
                margin: 20px 0;
            }
            
            .fa-spinner {
                color: #667eea;
            }
        """)
    ),
    
    ui.div(
        {"class": "main-container"},
        # 标题
        ui.h1("审计 AI 助手", class_="app-title"),
        ui.p("智能分析 · 专业报告 · 高效决策", class_="app-subtitle"),
        
        # 主要内容区域
        ui.layout_sidebar(
            ui.sidebar(
                ui.div(
                    {"class": "sidebar"},
                    ui.input_text_area(
                        "user_input",
                        "输入您的问题",
                        placeholder="请在这里输入您想要咨询的问题...",
                        rows=6,
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
                        "下载审计报告 (PDF)",
                        class_="btn-success",
                        width="100%"
                    ),
                ),
                width=420
            ),
            ui.card(
                ui.card_header("AI 分析结果"),
                ui.div(
                    {"class": "response-box"},
                    ui.output_ui("ai_response")
                ),
                ui.div(
                    {"class": "status-indicator"},
                    ui.output_text_verbatim("loading_status")
                )
            )
        )
    )
)

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
                api_key="sk-2d1d971450e441ea8d6f1526fc2d78c7",
                app_id='424abb0483f441a285f1c2b983276666',
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
            return ui.markdown(response_text)
        elif response_text == "正在思考中,请稍候...":
            return ui.div(
                ui.tags.i(class_="fa fa-spinner fa-spin"),
                " 正在思考中,请稍候...",
                class_="loading-text"
            )
        else:
            return ui.div(
                "💡 等待您的问题...",
                class_="waiting-text"
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
        
        # 使用 SimpleDocTemplate 创建 PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
        
        # 注册中文字体
        font_registered = False
        try:
            font_paths = [
                ('C:\\Windows\\Fonts\\simsun.ttc', 'SimSun'),
                ('C:\\Windows\\Fonts\\msyh.ttc', 'Microsoft YaHei'),
                ('C:\\Windows\\Fonts\\simhei.ttf', 'SimHei'),
                ('/System/Library/Fonts/PingFang.ttc', 'PingFang'),
                ('/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf', 'DroidSans'),
            ]
            
            for font_path, font_name in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont('CustomChinese', font_path))
                        font_registered = True
                        break
                    except:
                        continue
        except:
            pass
        
        # 创建样式
        styles = getSampleStyleSheet()
        
        # 标题样式
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor='black',
            spaceAfter=30,
            alignment=TA_LEFT,
            fontName='CustomChinese' if font_registered else 'Helvetica-Bold'
        )
        
        # 副标题样式
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor='black',
            spaceAfter=12,
            fontName='CustomChinese' if font_registered else 'Helvetica-Bold'
        )
        
        # 正文样式
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=11,
            leading=20,
            textColor='black',
            spaceAfter=12,
            fontName='CustomChinese' if font_registered else 'Helvetica',
            wordWrap='CJK'
        )
        
        # 小字样式
        small_style = ParagraphStyle(
            'CustomSmall',
            parent=styles['Normal'],
            fontSize=9,
            textColor='grey',
            fontName='Helvetica'
        )
        
        # 构建 PDF 内容
        story = []
        
        # 标题
        story.append(Paragraph("AI Audit Report", title_style))
        story.append(Spacer(1, 0.3*cm))
        
        # 生成时间
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", small_style))
        story.append(Spacer(1, 0.5*cm))
        
        # 分隔线 (使用表格模拟)
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib import colors
        line_table = Table([['']], colWidths=[doc.width])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0,0), (-1,0), 1, colors.grey),
        ]))
        story.append(line_table)
        story.append(Spacer(1, 0.5*cm))
        
        # 用户问题
        story.append(Paragraph("User Question:", heading_style))
        # 处理用户问题文本
        question_paragraphs = user_question.split('\n')
        for para in question_paragraphs:
            if para.strip():
                story.append(Paragraph(para, body_style))
        story.append(Spacer(1, 0.5*cm))
        
        # 分隔线
        story.append(line_table)
        story.append(Spacer(1, 0.5*cm))
        
        # AI 回复
        story.append(Paragraph("AI Response:", heading_style))
        # 处理 AI 回复文本
        response_paragraphs = response_text.split('\n')
        for para in response_paragraphs:
            if para.strip():
                # 替换 Markdown 标记为 HTML
                para = para.replace('**', '<b>').replace('**', '</b>')
                para = para.replace('##', '').replace('#', '')
                story.append(Paragraph(para, body_style))
        
        # 生成 PDF
        doc.build(story)
        
        # 重置 buffer 位置并返回
        buffer.seek(0)
        yield buffer.read()

# 创建应用
app = App(app_ui, server)
