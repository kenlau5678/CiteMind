# Demo course

`citemind-demo-course.pdf` and `citemind-demo-course-zh.pdf` are self-authored English and Chinese introductions to machine learning created specifically for CiteMind. They are released under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/); no private lecture notes or copyrighted course slides are included.

Regenerate it with:

```powershell
backend\.venv\Scripts\python sample-data\build_sample.py
backend\.venv\Scripts\python sample-data\build_sample_zh.py
```

`evaluation.json` and `evaluation-zh.json` contain two human-authored retrieval questions per page. The expected source is the PDF viewer page, not a printed page label.
