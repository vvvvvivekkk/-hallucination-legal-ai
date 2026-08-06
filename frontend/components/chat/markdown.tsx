"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownProps {
  content: string;
}

export function Markdown({ content }: MarkdownProps) {
  return (
    <div className="prose prose-sm prose-neutral max-w-none dark:prose-invert prose-headings:font-semibold prose-pre:bg-muted prose-pre:text-foreground prose-code:text-primary">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: (props) => (
            <a
              {...props}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-2"
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
