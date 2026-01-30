#!/usr/bin/env python3
"""
测试 STRM 任务管理系统
"""
import sys
import time
import json

# 测试导入
try:
    from lib115.config import AppConfig
    from lib115.db.factory import create_database
    from lib115.services.task_service import TaskService, StrmTask
    print("✓ 所有模块导入成功")
except Exception as e:
    print(f"✗ 模块导入失败: {e}")
    sys.exit(1)

# 测试数据库初始化
try:
    config = AppConfig.from_env()
    db = create_database(config)
    db.connect()
    print("✓ 数据库连接成功")

    # 检查表是否创建
    tables = ['strm_tasks', 'strm_records', 'file_snapshots', 'task_logs']
    for table in tables:
        try:
            result = db.fetchone(f"SELECT COUNT(*) as count FROM {table}")
            print(f"✓ 表 {table} 存在 (记录数: {result['count']})")
        except Exception as e:
            print(f"✗ 表 {table} 不存在或查询失败: {e}")

except Exception as e:
    print(f"✗ 数据库初始化失败: {e}")
    sys.exit(1)

# 测试任务服务
try:
    task_service = TaskService(db)
    print("✓ 任务服务初始化成功")

    # 测试创建任务
    task_data = {
        'task_name': '测试任务',
        'drive_id': 'test_drive',
        'source_cid': '0',
        'output_dir': '/tmp/test_strm',
        'base_url': 'http://localhost:8115',
        'include_video': True,
        'include_audio': False,
        'schedule_enabled': False,
        'watch_enabled': False,
        'delete_orphans': True,
        'preserve_structure': True
    }

    task = task_service.create_task(task_data)
    print(f"✓ 创建任务成功: {task.task_id}")

    # 测试获取任务
    retrieved_task = task_service.get_task(task.task_id)
    if retrieved_task:
        print(f"✓ 获取任务成功: {retrieved_task.task_name}")
    else:
        print("✗ 获取任务失败")

    # 测试列出任务
    tasks = task_service.list_tasks()
    print(f"✓ 列出任务成功: 共 {len(tasks)} 个任务")

    # 测试更新任务
    success = task_service.update_task(task.task_id, {
        'task_name': '测试任务（已更新）',
        'status': 'idle'
    })
    if success:
        print("✓ 更新任务成功")
    else:
        print("✗ 更新任务失败")

    # 测试任务统计
    stats = task_service.get_task_statistics(task.task_id)
    print(f"✓ 获取任务统计成功: {json.dumps(stats, indent=2, ensure_ascii=False)}")

    # 测试删除任务
    success = task_service.delete_task(task.task_id)
    if success:
        print("✓ 删除任务成功")
    else:
        print("✗ 删除任务失败")

except Exception as e:
    print(f"✗ 任务服务测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

finally:
    db.close()
    print("\n✓ 所有测试完成")
