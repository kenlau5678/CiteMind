from pathlib import Path

import fitz


PAGES = [
    ("1. What machine learning is", "Machine learning builds systems that improve a measurable task from data instead of relying only on hand-written rules. Supervised learning uses labelled examples. Unsupervised learning looks for structure without target labels. A useful project starts with a task metric and a representative evaluation set."),
    ("2. Train, validation, and test data", "Training data fits model parameters. Validation data guides model choice and hyperparameters. Test data estimates final performance and must remain untouched until the end. Data leakage occurs when information from validation or test examples influences training, producing an unrealistically optimistic result."),
    ("3. Linear models", "Linear regression predicts a continuous value with a weighted sum of features. Logistic regression models class probability through a sigmoid function. Regularization discourages overly large weights: L1 can create sparse weights while L2 smoothly shrinks them. Feature scaling improves optimization when feature ranges differ."),
    ("4. Neural networks and gradients", "A neural network composes affine transformations and nonlinear activation functions. Backpropagation applies the chain rule to compute the gradient of loss with respect to every parameter. Gradient descent updates parameters in the direction opposite the gradient. The learning rate controls the size of each update. For one scalar parameter, the update is theta_next = theta - eta * dL/dtheta."),
    ("5. Convolutional networks", "A convolutional layer applies shared filters across spatial locations. Weight sharing reduces parameter count and helps detect the same pattern in different positions. Pooling or strided convolution reduces spatial resolution. Receptive field describes the input region that can influence one activation."),
    ("6. Generalization", "Underfitting means the model cannot capture useful structure in training data. Overfitting means training performance is strong but performance on new data is poor. More representative data, regularization, augmentation, and early stopping can improve generalization. Model complexity should be selected with validation data."),
    ("7. Evaluation metrics", "Accuracy is the fraction of correct predictions but can hide failure on an imbalanced class. Precision measures how many predicted positives are correct. Recall measures how many actual positives are found. F1 is the harmonic mean of precision and recall. The metric must reflect the real cost of each error."),
    ("8. Embeddings and retrieval", "An embedding maps an item to a numeric vector whose geometry represents useful similarity. Semantic retrieval ranks items by vector similarity. Keyword retrieval is exact and strong for names, symbols, and rare terminology. Hybrid retrieval combines both signals and is often more reliable for mixed course material."),
    ("9. Responsible use", "A model can reproduce bias present in its training data. Evaluation should be split by relevant user groups when harms may differ. Privacy requires minimizing collected and transmitted data. Explanations are not evidence by themselves; important claims should be traceable to source material and checked by a person."),
    ("10. Reproducible experiments", "A reproducible experiment records the dataset version, code version, random seed, environment, hyperparameters, and evaluation procedure. A baseline provides a simple reference point. Change one important factor at a time when possible. Report failed experiments and uncertainty instead of selecting only favourable runs."),
]


def main():
    output = Path(__file__).with_name("citemind-demo-course.pdf")
    pdf = fitz.open()
    for page_number, (heading, body) in enumerate(PAGES, 1):
        page = pdf.new_page(width=595, height=842)
        page.insert_text((54, 55), "CITEMIND DEMO COURSE", fontsize=9, color=(0.28, 0.42, 0.36))
        page.insert_textbox((54, 92, 541, 165), heading, fontsize=23, fontname="hebo", color=(0.12, 0.18, 0.15))
        page.insert_textbox((54, 190, 541, 500), body, fontsize=13, lineheight=1.6, color=(0.22, 0.26, 0.24))
        if page_number == 4:
            page.draw_rect((92, 490, 503, 570), color=(0.72, 0.77, 0.73), fill=(0.95, 0.97, 0.94), width=1)
            page.insert_textbox(
                (112, 512, 483, 555), "theta_next = theta - eta * dL/dtheta",
                fontsize=18, fontname="hebo", align=fitz.TEXT_ALIGN_CENTER, color=(0.12, 0.25, 0.19),
            )
        page.insert_text((54, 785), f"Self-authored CC0 demo material - PDF page {len(pdf)}", fontsize=8, color=(0.5, 0.53, 0.51))
    pdf.save(output)
    pdf.close()
    print(output)


if __name__ == "__main__":
    main()
