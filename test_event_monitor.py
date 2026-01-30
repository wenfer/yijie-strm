#!/usr/bin/env python3
"""
测试事件监听功能
"""
import sys
import time
import logging
from lib115.api.client import Client115
from lib115.services.event_monitor import EventMonitor, EventProcessor, BEHAVIOR_TYPE_TO_NAME

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_event_api():
    """测试事件 API"""
    print("=" * 60)
    print("测试 1: 事件 API 调用")
    print("=" * 60)

    try:
        client = Client115()

        # 测试获取生活事件列表
        print("\n获取最近的生活事件...")
        result = client.get_life_behavior_list(limit=10)

        if result:
            print(f"✓ 成功获取事件列表")
            print(f"  总数: {result.get('count', 0)}")
            print(f"  返回: {len(result.get('list', []))} 条事件")

            # 显示前 3 条事件
            for i, event in enumerate(result.get('list', [])[:3], 1):
                event_type = event.get('type')
                event_name = BEHAVIOR_TYPE_TO_NAME.get(event_type, f"unknown_{event_type}")
                print(f"\n  事件 {i}:")
                print(f"    ID: {event.get('id')}")
                print(f"    类型: {event_name} ({event_type})")
                print(f"    文件: {event.get('file_name', 'N/A')}")
                print(f"    时间: {event.get('update_time', 'N/A')}")
        else:
            print("✗ 获取事件列表失败")
            return False

        client.close()
        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_monitor():
    """测试事件监听器"""
    print("\n" + "=" * 60)
    print("测试 2: 事件监听器")
    print("=" * 60)

    try:
        client = Client115()
        monitor = EventMonitor(client, cooldown=0.2)

        # 启动监听
        task_id = "test_task_001"
        source_cid = "0"  # 根目录

        print(f"\n启动监听 (task_id={task_id}, cid={source_cid})...")
        monitor.start_monitoring(
            task_id=task_id,
            source_cid=source_cid,
            callback=lambda events: print(f"检测到 {len(events)} 个事件"),
            from_event_id=0
        )

        # 检查事件
        print("\n检查新事件...")
        events = monitor.check_events(task_id, source_cid)

        if events:
            print(f"✓ 检测到 {len(events)} 个相关事件")

            # 处理事件
            changes = EventProcessor.process_events(events)
            summary = EventProcessor.summarize_changes(changes)
            print(f"  变更摘要: {summary}")

            # 显示详细信息
            for change_type, file_ids in changes.items():
                if file_ids:
                    print(f"  {change_type}: {len(file_ids)} 个文件")
        else:
            print("✓ 没有检测到新事件（这是正常的）")

        # 获取监听状态
        status = monitor.get_monitoring_status(task_id)
        if status:
            print(f"\n监听状态:")
            print(f"  任务 ID: {status['task_id']}")
            print(f"  最后事件 ID: {status['last_event_id']}")
            print(f"  最后检查时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status['last_check_time']))}")

        # 停止监听
        monitor.stop_monitoring(task_id)
        print("\n✓ 监听已停止")

        client.close()
        return True

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_types():
    """测试事件类型映射"""
    print("\n" + "=" * 60)
    print("测试 3: 事件类型映射")
    print("=" * 60)

    from lib115.services.event_monitor import (
        BEHAVIOR_TYPE_TO_NAME,
        SYNC_TRIGGER_TYPES,
        IGNORE_BEHAVIOR_TYPES
    )

    print("\n支持的事件类型:")
    for event_type, event_name in sorted(BEHAVIOR_TYPE_TO_NAME.items()):
        trigger = "✓" if event_type in SYNC_TRIGGER_TYPES else "✗"
        ignore = "(忽略)" if event_type in IGNORE_BEHAVIOR_TYPES else ""
        print(f"  {trigger} {event_type:2d}: {event_name:20s} {ignore}")

    print(f"\n触发同步的事件类型: {len(SYNC_TRIGGER_TYPES)} 个")
    print(f"忽略的事件类型: {len(IGNORE_BEHAVIOR_TYPES)} 个")

    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("115 网盘事件监听功能测试")
    print("=" * 60)

    results = []

    # 测试 1: 事件 API
    results.append(("事件 API 调用", test_event_api()))

    # 测试 2: 事件监听器
    results.append(("事件监听器", test_event_monitor()))

    # 测试 3: 事件类型映射
    results.append(("事件类型映射", test_event_types()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n✓ 所有测试通过！")
        return 0
    else:
        print("\n✗ 部分测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
