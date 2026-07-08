"""
从 CSV 文件导入 FQA 数据到 FqaEntry 模型的管理命令。

用法:
    python manage.py init_rag_data
    python manage.py init_rag_data --csv rag/data/JP学科知识问答.csv
"""
import os

import pandas as pd
from django.core.management.base import BaseCommand

from rag.models import FqaEntry


class Command(BaseCommand):
    help = '从 CSV 文件导入 FQA 问答对到 FqaEntry 模型'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv',
            type=str,
            default='rag/data/JP学科知识问答.csv',
            help='CSV 文件路径（相对于项目根目录）',
        )

    def handle(self, *args, **options):
        csv_path = options['csv']

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f'CSV 文件不存在: {csv_path}'))
            return

        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, encoding='gbk')
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'读取 CSV 文件失败: {e}'))
            return

        # 验证 CSV 列名
        expected_columns = {'学科名称', '问题', '答案'}
        actual_columns = set(df.columns)
        if not expected_columns.issubset(actual_columns):
            missing = expected_columns - actual_columns
            self.stderr.write(
                self.style.ERROR(
                    f'CSV 列名不匹配，缺少列: {missing}。'
                    f'实际列: {list(df.columns)}'
                )
            )
            return

        total = len(df)
        created_count = 0
        updated_count = 0
        error_count = 0

        self.stdout.write(f'开始导入 {total} 条 FQA 数据...')

        for idx, row in df.iterrows():
            try:
                subject_name = str(row['学科名称']).strip() if pd.notna(row['学科名称']) else ''
                question = str(row['问题']).strip() if pd.notna(row['问题']) else ''
                answer = str(row['答案']).strip() if pd.notna(row['答案']) else ''

                if not question:
                    self.stdout.write(
                        self.style.WARNING(f'第 {idx + 2} 行问题为空，跳过')
                    )
                    error_count += 1
                    continue

                obj, created = FqaEntry.objects.update_or_create(
                    question=question,
                    defaults={
                        'subject_name': subject_name,
                        'answer': answer,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

                # 每 100 条打印一次进度
                if (idx + 1) % 100 == 0:
                    self.stdout.write(
                        f'已处理 {idx + 1}/{total} 条...'
                    )

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'第 {idx + 2} 行处理失败: {e}'
                    )
                )

        self.stdout.write(self.style.SUCCESS(
            f'\n导入完成！\n'
            f'  总计: {total} 条\n'
            f'  新增: {created_count} 条\n'
            f'  更新: {updated_count} 条\n'
            f'  跳过/错误: {error_count} 条\n'
        ))
