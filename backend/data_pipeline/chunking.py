import re

def make_chunk(source: str,chunk_id:int, heading: str, content: str, parent: str = '') -> dict:

    return {"source": source,"chunk_id":chunk_id, "heading": heading, "parent":parent, "content": content.strip()}

def parse_md_to_chunks(filepath: str, source_name: str) -> list[dict]:
    text = open(filepath, encoding="utf-8").read()
    document_chunks = []
    document_chunk_n = 0
    blocks = re.split( rf'\n(?={"##"} )', text)
    for block in blocks:
        top_heading = re.match(rf'{"##"} (.+)', block)

        if not top_heading:
            # preamble
            heading = 'preamble'
            chunk = make_chunk(source_name,document_chunk_n, heading, block.replace('---','').strip())
            document_chunk_n += 1
            document_chunks.append(chunk)

            continue

        section_title = top_heading.group(1).strip()
        content_after_heading = block.split('\n', 1)[1] if '\n' in block else ""
        sub_blocks = re.split(r'\n(?=### )', content_after_heading)
        first_block = sub_blocks[0].strip()

        if first_block and not first_block.startswith("### "):
            chunk = make_chunk(source_name, document_chunk_n, section_title,
                               first_block.replace('---', '').strip())
            document_chunk_n += 1
            document_chunks.append(chunk)
            sub_blocks = sub_blocks[1:]  # remove it so we don’t process twice

        # subheadings
        for sub_block in sub_blocks:
            sub_heading = re.match(r'### (.+)', sub_block)
            if sub_heading:
                sub_title = sub_heading.group(1).strip()
                content = sub_block.split('\n', 1)[1] if '\n' in sub_block else ""
                chunk = make_chunk(source_name,document_chunk_n, sub_title,
                                   content.replace('---', '').strip(),section_title)
                document_chunk_n += 1
                document_chunks.append(chunk)

    return document_chunks