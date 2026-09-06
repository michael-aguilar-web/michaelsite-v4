import type { CollectionEntry } from 'astro:content';

export interface WikiNode {
  id: string;
  title: string;
  order: number;
  href?: string;
  children: WikiNode[];
}

// Content-independent tree building, kept separate for a future shared wiki package.
export function buildWikiTree(notes: CollectionEntry<'wiki'>[]): WikiNode[] {
  const nodes = new Map<string, WikiNode>();
  function ensure(id: string): WikiNode {
    let node = nodes.get(id);
    if (!node) {
      node = { id, title: id.split('/').at(-1)!.replaceAll('-', ' '), order: 10, children: [] };
      nodes.set(id, node);
      const parent = id.split('/').slice(0, -1).join('/');
      if (parent) ensure(parent).children.push(node);
    }
    return node;
  }
  for (const note of notes.filter((note) => !note.data.draft)) {
    Object.assign(ensure(note.id), { title: note.data.title, order: note.data.order, href: `/wiki/${note.id}/` });
  }
  function sort(nodes: WikiNode[]): WikiNode[] {
    return nodes.sort((a, b) => a.order - b.order || a.title.localeCompare(b.title)).map((node) => ({ ...node, children: sort(node.children) }));
  }
  return sort([...nodes.values()].filter((node) => !node.id.includes('/')));
}
