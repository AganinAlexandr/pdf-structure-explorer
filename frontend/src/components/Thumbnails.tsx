import { memo } from "react";
import { api, PageSummary } from "../api";

interface Props {
  documentId: string;
  pages: PageSummary[];
  current: number;
  onSelect: (n: number) => void;
}

export const Thumbnails = memo(function Thumbnails(p: Props) {
  return (
    <nav className="thumbs">
      {p.pages.map((pg) => (
        <button
          key={pg.pageNumber}
          className={"thumb" + (pg.pageNumber === p.current ? " active" : "")}
          onClick={() => p.onSelect(pg.pageNumber)}
          title={`Стр. ${pg.pageNumber}: элементов ${pg.elementCount}, таблиц ${pg.tableCount}`}
        >
          <img
            src={api.previewUrl(p.documentId, pg.pageNumber, 0.15)}
            alt={`Стр. ${pg.pageNumber}`}
            loading="lazy"
          />
          <span className="mono">{pg.pageNumber}</span>
          {pg.tableCount > 0 && <span className="tmark">{pg.tableCount} табл.</span>}
        </button>
      ))}
    </nav>
  );
});
