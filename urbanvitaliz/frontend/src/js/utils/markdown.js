import { marked } from 'marked';

export function renderMarkdown(content) {
    return marked.parse(content);
}
