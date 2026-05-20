# 发布指南

> gxu-wjxt Monorepo 双 SDK 发布流程

---

## 目录

1. [版本管理](#1-版本管理)
2. [Python SDK 发布 (PyPI)](#2-python-sdk-发布-pypi)
3. [Node.js SDK 发布 (npm)](#3-nodejs-sdk-发布-npm)
4. [发布 Checklist](#4-发布-checklist)

---

## 1. 版本管理

两个 SDK 目前保持**独立版本号**，遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

| SDK | 版本文件 | 当前版本 |
|-----|---------|---------|
| Python `gxu-wjxt` | `packages/python/pyproject.toml` → `[project] version` | `1.2.0` |
| Node.js `@gxuwjxt/node` | `packages/node/package.json` → `version` | `1.2.0` |

**发版前必须手动更新对应版本号。**

---

## 2. Python SDK 发布 (PyPI)

### 2.1 前置条件

```bash
pip install build twine
```

### 2.2 发布到 TestPyPI（推荐先验证）

```bash
cd packages/python

# 清理旧产物 → 构建 → 上传测试仓库
make pub-test
```

或手动三步：

```bash
cd packages/python

# 1. 清理旧构建产物
rm -rf dist/*

# 2. 构建 (生成 .whl 和 .tar.gz)
python -m build

# 3. 上传到 TestPyPI
twine upload -r testpypi dist/*
```

### 2.3 验证 TestPyPI 安装

```bash
pip install --index-url https://test.pypi.org/simple/ gxu-wjxt
python -c "from gxu_wjxt import WjxtClient; print('OK')"
```

### 2.4 发布到正式 PyPI

```bash
cd packages/python

# 一键发布
make pub
```

或手动：

```bash
cd packages/python

rm -rf dist/*
python -m build
twine upload dist/*
```

### 2.5 发布文件说明

构建后在 `packages/python/dist/` 生成：

```
gxu_wjxt-1.2.0-py3-none-any.whl    # Wheel 格式
gxu_wjxt-1.2.0.tar.gz              # 源码包
```

### 2.6 涉及文件

| 文件 | 作用 |
|------|------|
| `packages/python/pyproject.toml` | 包名、版本、依赖、构建配置 |
| `packages/python/Makefile` | 构建/上传快捷命令（自动拷贝 README） |
| `packages/python/src/gxu_wjxt/` | 源码（9 个模块） |
| `README.md`（根目录） | 构建时拷贝到 `packages/python/README.md`，用作 PyPI 项目描述 |

> **注意：** `pyproject.toml` 中 `readme = "README.md"` 指向 `packages/python/README.md`。
> 此文件由 `make build` 自动从根目录 `../../README.md` 拷贝，构建后由 `make clean` 删除。不要手动编辑或提交它。

---

## 3. Node.js SDK 发布 (npm)

### 3.1 前置条件

- Node.js >= 18
- npm 账号（[注册](https://www.npmjs.com/signup)）
- npm 登录：`npm login`

### 3.2 构建

```bash
# 从 monorepo 根目录
pnpm build:node
```

产物在 `packages/node/dist/`：

```
dist/
├── index.js       # ESM 入口
├── index.cjs      # CJS 入口
├── index.d.ts     # TypeScript 类型声明
└── index.d.cts    # CJS 类型声明
```

### 3.3 发布到 npm

```bash
cd packages/node

# 干跑预览（不实际发布，检查哪些文件会被包含）
npm publish --dry-run
```

核对输出中 `files` 列表，确认只包含需要的文件。发布文件由 `package.json` 的 `"files"` 字段控制：

```json
"files": [
  "dist",
  "GUIDE.md"
]
```

确认无误后正式发布：

```bash
cd packages/node
npm publish
```

> 注意：首次发布使用 `npm publish`，后续发布如遇「无法覆盖」错误，需更新 `version` 字段后使用 `npm publish`。也可用 `npm publish --access public` 显式指定公开包（scoped 包首次发布必须）。

### 3.4 验证 npm 安装

```bash
npm install @gxuwjxt/node
node -e "const { WjxtClient } = require('@gxuwjxt/node'); console.log('OK');"
```

TypeScript 项目中验证类型：

```typescript
import type { FileInfo, SearchResult } from '@gxuwjxt/node';
```

### 3.5 涉及文件

| 文件 | 作用 |
|------|------|
| `packages/node/package.json` | 包名、版本、依赖、`"files"` 发布列表 |
| `packages/node/tsconfig.json` | TypeScript 编译配置 |
| `packages/node/src/` | 源码（7 个模块） |
| `packages/node/dist/` | 构建产物（被发布，被 gitignore） |
| `packages/node/GUIDE.md` | 使用指南（随包发布） |

### 3.6 快捷脚本（可选）

可在根 `package.json` 中添加 publish 脚本：

```json
"scripts": {
  "build:node": "pnpm -r --filter @gxuwjxt/node build",
  "test:node": "pnpm -r --filter @gxuwjxt/node test",
  "publish:node": "pnpm -r --filter @gxuwjxt/node publish"
}
```

---

## 4. 发布 Checklist

### 事前检查

- [ ] 所有测试通过：`pnpm test:node` + `pytest packages/python/`
- [ ] TypeScript 编译无错误：`cd packages/node && npx tsc --noEmit`
- [ ] Python 导入正常：`python -c "import sys; sys.path.insert(0,'packages/python/src'); from gxu_wjxt import WjxtClient"`
- [ ] 工作树干净：`git status`

### 发版步骤

1. **更新版本号**

   Python：编辑 `packages/python/pyproject.toml` 中 `version`
   Node.js：编辑 `packages/node/package.json` 中 `version`

2. **提交版本变更**

   ```bash
   git add packages/python/pyproject.toml packages/node/package.json
   git commit -m "chore: bump version to X.Y.Z"
   ```

3. **发布 Python → PyPI**

   ```bash
   cd packages/python && make pub
   ```

4. **发布 Node.js → npm**

   ```bash
   pnpm build:node && cd packages/node && npm publish
   ```

5. **推送 + 打 Tag**

   ```bash
   git push origin main
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

### 发布清单速查

| 步骤 | Python SDK | Node.js SDK |
|------|-----------|-------------|
| 注册表 | [PyPI](https://pypi.org) | [npm](https://npmjs.com) |
| 包名 | `gxu-wjxt` | `@gxuwjxt/node` |
| 构建命令 | `cd packages/python && python -m build` | `pnpm build:node` |
| 发布命令 | `twine upload dist/*` | `npm publish`（在 packages/node/ 下） |
| 测试发布 | TestPyPI | `npm publish --dry-run` |
| 认证 | `twine` 凭据 / `~/.pypirc` | `npm login` |
