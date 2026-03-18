# Edict 自动化测试命令

.PHONY: test test-unit test-integration test-all test-coverage install

# 安装依赖
install:
	pip install -r requirements.txt

# 运行所有测试
test: test-unit

# 单元测试
test-unit:
	pytest tests/test_suite.py -v --tb=short

# 集成测试
test-integration:
	pytest tests/test_kanban.py tests/test_e2e_kanban.py -v

# 边界测试
test-edge:
	pytest tests/test_edge_cases.py -v

# 并发测试
test-concurrency:
	pytest tests/test_concurrency.py -v

# 覆盖率测试
test-coverage:
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term

# 快速测试 (跳过慢速测试)
test-quick:
	pytest tests/test_suite.py -v -k "not integration"

# lint
lint:
	pylint scripts/ --disable=C0114,C0115,C0116 || true

# 格式化
format:
	black scripts/ tests/ || true

# 完整检查
check: install lint test

# 帮助
help:
	@echo "可用命令:"
	@echo "  make install        - 安装依赖"
	@echo "  make test          - 运行单元测试"
	@echo "  make test-integration - 运行集成测试"
	@echo "  make test-coverage - 运行覆盖率测试"
	@echo "  make test-quick    - 快速测试"
	@echo "  make lint          - 代码检查"
	@echo "  make format        - 代码格式化"
	@echo "  make check         - 完整检查"
