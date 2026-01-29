#!/usr/bin/env python3
"""
lib115 使用示例

演示如何使用 lib115 库进行常见操作
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib115 import Client115, FileService, StrmService, format_bytes


def example_list_files():
    """示例：列出文件"""
    print("\n=== 列出根目录文件 ===")

    with Client115() as client:
        items, total = client.list_files('0', limit=10)
        print(f"总数: {total}")
        for item in items:
            name = item.get('fn') or item.get('file_name')
            size = item.get('fs') or item.get('file_size', 0)
            is_dir = (item.get('fc') or item.get('file_category')) == '0'
            type_str = '[DIR]' if is_dir else '[FILE]'
            print(f"  {type_str} {name} ({format_bytes(int(size) if size else 0)})")


def example_search():
    """示例：搜索文件"""
    print("\n=== 搜索文件 ===")

    keyword = input("请输入搜索关键词: ").strip()
    if not keyword:
        print("未输入关键词")
        return

    with Client115() as client:
        items, total = client.search(keyword, limit=10)
        print(f"找到 {total} 个结果:")
        for item in items:
            name = item.get('fn') or item.get('file_name')
            print(f"  - {name}")


def example_get_download_url():
    """示例：获取下载链接"""
    print("\n=== 获取下载链接 ===")

    pick_code = input("请输入 pick_code: ").strip()
    if not pick_code:
        print("未输入 pick_code")
        return

    with Client115() as client:
        url = client.get_download_url(pick_code)
        if url:
            print(f"下载链接: {url}")
        else:
            print("获取下载链接失败")


def example_traverse_folder():
    """示例：遍历文件夹"""
    print("\n=== 遍历文件夹 ===")

    cid = input("请输入文件夹 CID (默认 0): ").strip() or '0'

    with Client115() as client:
        file_service = FileService(client)

        file_count = 0
        folder_count = 0
        total_size = 0

        def count_item(item):
            nonlocal file_count, total_size
            file_count += 1
            size = item.get('fs') or item.get('file_size', 0)
            total_size += int(size) if size else 0

        def count_folder(item):
            nonlocal folder_count
            folder_count += 1

        print("正在遍历...")
        items = file_service.traverse_folder(
            cid, "",
            item_handler=count_item,
            folder_handler=count_folder,
            max_depth=2  # 限制深度为 2
        )

        print(f"文件数: {file_count}")
        print(f"文件夹数: {folder_count}")
        print(f"总大小: {format_bytes(total_size)}")


def example_generate_strm():
    """示例：生成 STRM 文件"""
    print("\n=== 生成 STRM 文件 ===")

    cid = input("请输入文件夹 CID: ").strip()
    if not cid:
        print("未输入 CID")
        return

    output_dir = input("请输入输出目录: ").strip()
    if not output_dir:
        print("未输入输出目录")
        return

    base_url = input("请输入基础 URL (如 http://localhost:8115): ").strip()

    with Client115() as client:
        file_service = FileService(client)
        strm_service = StrmService(file_service)

        print("正在生成 STRM 文件...")
        strm_files = strm_service.generate_strm_files(
            root_cid=cid,
            output_dir=output_dir,
            base_url=base_url
        )

        print(f"生成了 {len(strm_files)} 个 STRM 文件")
        for strm in strm_files[:5]:  # 只显示前 5 个
            print(f"  - {strm.path}")
        if len(strm_files) > 5:
            print(f"  ... 还有 {len(strm_files) - 5} 个")


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    lib115 使用示例                            ║
╚══════════════════════════════════════════════════════════════╝

请选择示例:
  1. 列出文件
  2. 搜索文件
  3. 获取下载链接
  4. 遍历文件夹
  5. 生成 STRM 文件
  0. 退出
""")

    examples = {
        '1': example_list_files,
        '2': example_search,
        '3': example_get_download_url,
        '4': example_traverse_folder,
        '5': example_generate_strm,
    }

    while True:
        choice = input("\n请选择 (0-5): ").strip()
        if choice == '0':
            print("再见!")
            break
        elif choice in examples:
            try:
                examples[choice]()
            except Exception as e:
                print(f"错误: {e}")
        else:
            print("无效选择")


if __name__ == '__main__':
    main()
