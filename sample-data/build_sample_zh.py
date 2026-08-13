from pathlib import Path

import fitz


PAGES = [
    ("一、机器学习的基本类型", "监督学习使用带有目标标签的样本来学习输入与输出之间的映射。无监督学习没有目标标签，主要发现数据中的结构、聚类或低维表示。选择学习方式之前，应该先明确任务目标和评价指标。"),
    ("二、训练集、验证集与测试集", "训练集用于拟合模型参数，验证集用于选择模型和超参数，测试集只用于最终评估。测试集的信息如果在训练阶段被使用，就会发生数据泄漏，导致评估结果过于乐观，无法代表模型面对新数据时的表现。"),
    ("三、神经网络与反向传播", "神经网络通过多层线性变换和非线性激活函数表示复杂关系。反向传播利用链式法则计算损失函数对每个参数的梯度。梯度下降沿梯度的反方向更新参数，而学习率决定每次参数更新的步长。"),
    ("四、卷积神经网络", "卷积层让同一个滤波器在不同空间位置共享权重，因此能够减少参数数量，并在不同位置识别相同模式。感受野表示某个激活值能够受到输入图像中多大区域的影响。池化或步幅卷积可以降低空间分辨率。"),
    ("五、嵌入与混合检索", "嵌入把文本映射为数值向量，使语义相近的内容在向量空间中更加接近。关键词检索擅长匹配人名、符号和罕见术语，语义检索擅长理解自然语言含义。混合检索融合两种信号，对包含专业术语和自然语言问题的课程资料通常更可靠。"),
]


def find_font() -> Path:
    candidates = [
        Path(r"C:\Windows\Fonts\Deng.ttf"),
        Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit("No supported CJK font found; the committed demo PDF can still be used directly.")


def main():
    output = Path(__file__).with_name("citemind-demo-course-zh.pdf")
    font = find_font()
    pdf = fitz.open()
    for heading, body in PAGES:
        page = pdf.new_page(width=595, height=842)
        page.insert_font(fontname="notosc", fontfile=str(font))
        page.insert_text((54, 55), "CITEMIND 中文示例课程", fontsize=9, fontname="notosc", color=(0.28, 0.42, 0.36))
        page.insert_textbox((54, 92, 541, 165), heading, fontsize=23, fontname="notosc", color=(0.12, 0.18, 0.15))
        page.insert_textbox((54, 190, 541, 540), body, fontsize=13, fontname="notosc", lineheight=1.7, color=(0.22, 0.26, 0.24))
        page.insert_text((54, 785), f"自编 CC0 示例资料 · PDF 第 {len(pdf)} 页", fontsize=8, fontname="notosc", color=(0.5, 0.53, 0.51))
    pdf.subset_fonts()
    pdf.save(output, garbage=4, deflate=True)
    pdf.close()
    print(output)


if __name__ == "__main__":
    main()
