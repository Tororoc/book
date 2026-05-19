# Git LFS 上传大数据教程

本仓库已经添加 `.gitattributes`，会用 Git LFS 管理 `data/**` 目录以及常见大文件格式，例如 `.zip`、`.tif`、`.nc`、`.xlsx`、`.h5`、`.shp` 等。

建议把 1.5G 数据放到仓库的 `data/` 目录下再提交。这样即使文件扩展名没有被单独列出，也会自动走 LFS。

## 1. 安装 Git LFS

Windows 推荐安装 Git for Windows 后，在 PowerShell 或 Git Bash 中执行：

```bash
git lfs install
```

macOS：

```bash
brew install git-lfs
git lfs install
```

Ubuntu/Debian：

```bash
sudo apt update
sudo apt install git-lfs
git lfs install
```

检查是否安装成功：

```bash
git lfs version
```

## 2. 拉取最新仓库

如果本机已经有这个仓库：

```bash
cd /path/to/book
git pull origin main
```

如果本机还没有仓库：

```bash
git clone git@github.com:Tororoc/book.git
cd book
git lfs install
```

如果你使用的是本机自定义 SSH host，例如 `github-cj`，clone 地址按你的 SSH 配置改成：

```bash
git clone git@github-cj:Tororoc/book.git
cd book
git lfs install
```

## 3. 放入大数据文件

推荐目录结构：

```text
book/
  data/
    your_large_dataset.zip
```

命令示例：

```bash
mkdir -p data
cp /path/to/your_large_dataset.zip data/
```

如果你的数据不放在 `data/` 目录，且扩展名没有被 `.gitattributes` 覆盖，需要先手动添加 LFS 规则：

```bash
git lfs track "path/to/your_large_file.ext"
git add .gitattributes
```

## 4. 确认文件会走 LFS

添加文件前后都可以检查：

```bash
git check-attr filter -- data/your_large_dataset.zip
```

如果输出包含 `filter: lfs`，说明该文件会通过 LFS 上传。

也可以在 `git add` 后检查：

```bash
git add data/your_large_dataset.zip
git lfs status
```

## 5. 提交并推送

```bash
git add data/your_large_dataset.zip
git commit -m "Add large dataset with Git LFS"
git push origin main
```

推送时 Git 会先上传 LFS 对象，再上传普通 Git commit。

## 6. 验证上传结果

本地检查 LFS 跟踪文件：

```bash
git lfs ls-files
```

确认 Git 里保存的是 LFS 指针，而不是 1.5G 原文件内容：

```bash
git show HEAD:data/your_large_dataset.zip | head
```

正常会看到类似内容：

```text
version https://git-lfs.github.com/spec/v1
oid sha256:...
size ...
```

## 注意事项

- 1.5G 文件不能用普通 Git 提交，必须先确认 `git check-attr` 输出 `filter: lfs`。
- GitHub LFS 有账号/组织配额和单文件大小限制；1.5G 通常需要确认当前账号或组织的 LFS quota 足够。
- 如果你已经把大文件普通提交过，需要做历史清理，不能只删除文件后重新提交。
- 其他人 clone 后如果没有自动拉到真实文件，可以运行 `git lfs pull`。

