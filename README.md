# Scientific Provenance Datahub

记录科研运行所使用的数据集、代码版本、参数、产物和父级运行，生成可追溯的血缘边和可复现实验指纹。它保留不可变运行事实，也提供适合分析和重跑检测的 SQLite 数据集。

## 运行

```bash
PYTHONPATH=src python3 -m scientific_provenance.cli \
  --fixture fixtures/sample.json \
  --database /tmp/scientific-provenance-datahub.sqlite3
```

## 外部依赖类型与版本

- Python 3.11+
- SQLite 3.x
- pytest 8.3.x（测试）

示例中的路径、数据集和代码版本均为虚构值，不写入真实账号、连接串、token 或密钥。

## 验证

```bash
PYTHONPATH=src python3 -m pytest --import-mode=importlib tests
PYTHONPATH=src python3 -m compileall -q src
```
