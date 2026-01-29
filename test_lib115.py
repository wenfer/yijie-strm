#!/usr/bin/env python3
"""
lib115 模块结构测试
验证所有模块是否可以正确导入
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """测试所有模块导入"""
    print("=== 测试模块导入 ===\n")

    tests = [
        ("config", "from lib115.config import AppConfig, default_config"),
        ("auth", "from lib115.auth import TokenManager, TokenWatcher"),
        ("api", "from lib115.api import Client115, is_folder, get_item_attr"),
        ("services.file_service", "from lib115.services import FileService, FileIndex"),
        ("services.strm_service", "from lib115.services import StrmService, StrmGenerator"),
        ("gateway", "from lib115.gateway import GatewayServer, run_gateway"),
        ("utils", "from lib115.utils import format_bytes, parse_size, safe_filename"),
        ("main package", "from lib115 import Client115, StrmService, GatewayServer"),
    ]

    passed = 0
    failed = 0

    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"  ✓ {name}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed += 1

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_config():
    """测试配置模块"""
    print("\n=== 测试配置模块 ===\n")

    from lib115.config import AppConfig, default_config

    # 测试默认配置
    assert default_config.api.FILE_LIST_API_URL == "https://proapi.115.com/open/ufile/files"
    print("  ✓ 默认 API URL 正确")

    assert default_config.gateway.PORT == 8115
    print("  ✓ 默认网关端口正确")

    # 测试从环境变量加载
    os.environ['GATEWAY_PORT'] = '9000'
    config = AppConfig.from_env()
    assert config.gateway.PORT == 9000
    print("  ✓ 环境变量加载正确")
    del os.environ['GATEWAY_PORT']

    print("\n配置模块测试通过!")
    return True


def test_utils():
    """测试工具模块"""
    print("\n=== 测试工具模块 ===\n")

    from lib115.utils import format_bytes, parse_size, safe_filename, parse_indices

    # 测试 format_bytes
    assert format_bytes(0) == "0 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"
    print("  ✓ format_bytes 正确")

    # 测试 parse_size
    assert parse_size("0B") == 0
    assert parse_size("1KB") == 1024
    assert parse_size("1.5GB") == int(1.5 * 1024 ** 3)
    print("  ✓ parse_size 正确")

    # 测试 safe_filename
    assert safe_filename("test.txt") == "test.txt"
    assert safe_filename("test/file.txt") == "test_file.txt"
    assert safe_filename("") == "unnamed_file"
    print("  ✓ safe_filename 正确")

    # 测试 parse_indices
    assert parse_indices("0", 10) == [0]
    assert parse_indices("0-3", 10) == [0, 1, 2, 3]
    assert parse_indices("0,2,4", 10) == [0, 2, 4]
    assert parse_indices("a", 5) == [0, 1, 2, 3, 4]
    print("  ✓ parse_indices 正确")

    print("\n工具模块测试通过!")
    return True


def test_api_helpers():
    """测试 API 辅助函数"""
    print("\n=== 测试 API 辅助函数 ===\n")

    from lib115.api import is_folder, get_item_attr

    # 测试 is_folder
    assert is_folder({"fc": "0"}) == True
    assert is_folder({"fc": "1"}) == False
    assert is_folder({"file_category": "0"}) == True
    print("  ✓ is_folder 正确")

    # 测试 get_item_attr
    item = {"fn": "test.txt", "file_name": "test2.txt", "fs": 1024}
    assert get_item_attr(item, "fn", "file_name") == "test.txt"
    assert get_item_attr(item, "xxx", default="default") == "default"
    print("  ✓ get_item_attr 正确")

    print("\nAPI 辅助函数测试通过!")
    return True


def test_strm_service():
    """测试 STRM 服务"""
    print("\n=== 测试 STRM 服务 ===\n")

    from lib115.services.strm_service import StrmService, VIDEO_EXTENSIONS

    # 测试视频扩展名
    assert ".mp4" in VIDEO_EXTENSIONS
    assert ".mkv" in VIDEO_EXTENSIONS
    print("  ✓ VIDEO_EXTENSIONS 正确")

    # 测试 extract_pick_code (不需要实际连接)
    class MockFileService:
        def get_download_url(self, pick_code, use_cache=True):
            return f"http://example.com/{pick_code}"

    # 创建一个简单的 mock
    strm_service = StrmService.__new__(StrmService)
    strm_service.config = None
    strm_service.file_service = MockFileService()
    strm_service._index = None

    # 测试 extract_pick_code
    assert strm_service.extract_pick_code("strm://115/abc123") == "abc123"
    assert strm_service.extract_pick_code("http://localhost:8115/stream/xyz789") == "xyz789"
    assert strm_service.extract_pick_code("abc123") == "abc123"
    print("  ✓ extract_pick_code 正确")

    print("\nSTRM 服务测试通过!")
    return True


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    lib115 模块测试                            ║
╚══════════════════════════════════════════════════════════════╝
""")

    all_passed = True

    all_passed &= test_imports()
    all_passed &= test_config()
    all_passed &= test_utils()
    all_passed &= test_api_helpers()
    all_passed &= test_strm_service()

    print("\n" + "=" * 50)
    if all_passed:
        print("✓ 所有测试通过!")
    else:
        print("✗ 部分测试失败")

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
