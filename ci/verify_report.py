"""核对本次 UI 结果和开始截图，复制 HTML 到 Jenkins 固定发布目录。"""
import json
from pathlib import Path
import shutil


def verify(root: Path) -> dict:
    metadata = json.loads((root / 'latest.json').read_text(encoding='utf-8'))
    results = Path(metadata['results']).resolve()
    if results != (root / 'ui-results').resolve():
        raise ValueError('latest.json 不属于本次 UI 运行')
    if metadata['report_error'] or not metadata['html']:
        raise ValueError(f"HTML 生成失败：{metadata['report_error']}")
    html = Path(metadata['html'])
    if not html.is_file():
        raise FileNotFoundError(html)
    records = [json.loads(p.read_text(encoding='utf-8')) for p in results.glob('*-result.json')]
    if not records:
        raise ValueError('没有 UI 用例结果')

    def screenshots(steps):
        count = 0
        for step in steps:
            for attachment in step.get('attachments', []):
                if attachment.get('name', '').startswith('步骤开始：'):
                    image = (results / attachment['source']).resolve()
                    if not image.is_relative_to(results) or not image.is_file():
                        raise ValueError('截图附件不存在或路径越界')
                    if not image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):
                        raise ValueError('开始截图不是有效 PNG')
                    count += 1
            count += screenshots(step.get('steps', []))
        return count

    summary = []
    missing = []
    for record in records:
        count = screenshots(record.get('steps', []))
        summary.append({'name': record['name'], 'status': record['status'], 'start_screenshots': count})
        if record['status'] == 'passed' and count == 0:
            missing.append(record['name'])
    # 即使测试失败，也发布已有的完整报告。
    shutil.copytree(html.parent, root / 'ui-html', dirs_exist_ok=True)
    output = {'run_id': metadata['run_id'], 'cases': summary, 'missing_screenshots': missing}
    (root / 'ci-verification.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    if missing:
        raise ValueError(f'通过用例缺少开始截图：{missing}')
    if metadata['pytest_exit_status'] != 0 or any(r['status'] != 'passed' for r in records):
        raise ValueError('UI 用例未全部通过，报告已保留')
    return output


if __name__ == '__main__':
    print(json.dumps(verify(Path('report').resolve()), ensure_ascii=False))
