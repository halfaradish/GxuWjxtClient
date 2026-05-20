# 清理打包产物
clean:
	rm -rf dist/*

# 打包项目（生成 dist 发布文件）
build:
	python -m build

# 单独上传 → TestPyPI（测试仓库）
upload-test:
	twine upload -r testpypi dist/*

# 单独上传 → 正式 PyPI（生产仓库）
upload:
	twine upload dist/*

# 一键发布 → TestPyPI（测试用，推荐优先使用）
pub-test:
	make clean
	make build
	make upload-test

# 一键发布 → 正式 PyPI（最终发布，谨慎使用）
pub:
	make clean
	make build
	make upload