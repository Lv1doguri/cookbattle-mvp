import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Screen, Header, TopBar, IconButton } from '../components/Screen';
import TabBar from '../components/TabBar';
import Icon from '../components/Icon';
import { Badge, Chip, FoodThumb } from '../components/ui';
import { QUICK_FILTERS, RECIPES, applyFilters, skillLabel, won } from '../data/mock';
import { useApp } from '../state/AppContext';

const SORTS = [
  { id: 'latest', label: '최신순', fn: (a, b) => b.createdAt.localeCompare(a.createdAt) },
  { id: 'popular', label: '저장순', fn: (a, b) => b.saves - a.saves },
  { id: 'cheap', label: '저렴한순', fn: (a, b) => a.cost - b.cost },
];

export default function Recipes() {
  const { filters, savedIds, toggleSaved } = useApp();
  const [query, setQuery] = useState('');
  const [quick, setQuick] = useState('all');
  const [sortIdx, setSortIdx] = useState(0);

  const activeFilterCount = Object.values(filters).flat().length;

  const list = useMemo(() => {
    const q = query.trim();
    const quickTest = QUICK_FILTERS.find((f) => f.id === quick)?.test;
    return applyFilters(RECIPES, filters)
      .filter((r) => !quickTest || quickTest(r))
      .filter((r) => !q || r.name.includes(q) || r.category.includes(q) || r.ingredients.some(([n]) => n.includes(q)))
      .sort(SORTS[sortIdx].fn);
  }, [query, quick, sortIdx, filters]);

  return (
    <Screen>
      <Header className="recipes-hdr">
        <TopBar title="레시피" brand>
          <IconButton label={`필터${activeFilterCount ? ` ${activeFilterCount}개 적용됨` : ''}`} to="/recipes/filter" dot={activeFilterCount > 0}>
            <Icon name="filter" size={22} />
          </IconButton>
        </TopBar>
        <label className="search">
          <Icon name="search" size={20} strokeWidth={2.2} />
          <input
            type="search" aria-label="검색" placeholder="재료, 요리 이름, 키워드 검색"
            value={query} onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <div className="chips-row">
          {QUICK_FILTERS.map((f) => (
            <Chip key={f.id} on={quick === f.id} onClick={() => setQuick(f.id)}>{f.label}</Chip>
          ))}
        </div>
      </Header>

      <div className="list-meta">
        <span className="list-meta__count">{list.length}개 결과</span>
        <button type="button" className="list-meta__sort" onClick={() => setSortIdx((sortIdx + 1) % SORTS.length)}>
          {SORTS[sortIdx].label}<Icon name="chevronDown" size={14} strokeWidth={2.5} />
        </button>
      </div>

      <div className="body">
        <div className="stack pad-x" style={{ gap: 10, paddingBottom: 16 }}>
          {list.map((r) => {
            const saved = savedIds.includes(r.id);
            return (
              <div key={r.id} className="card rc">
                <Link to={`/recipes/${r.id}`} className="rc__link">
                  <FoodThumb tone={r.tone} size={92} />
                  <div className="rc__info">
                    <Badge className="rc__award">{r.award}</Badge>
                    <span className="rc__name">{r.name}</span>
                    <span className="meta"><Icon name="clock" size={14} strokeWidth={2.2} />{r.minutes}분 · ₩{won(r.cost)}</span>
                    <span className="rc__sub">{skillLabel(r.skill)} · 저장 {r.saves + (saved ? 1 : 0)}</span>
                  </div>
                </Link>
                <button
                  type="button" className={`bm ${saved ? 'on' : ''}`} aria-pressed={saved}
                  aria-label={saved ? '저장 취소' : '저장'} onClick={() => toggleSaved(r.id)}
                >
                  <Icon name="bookmark" size={18} strokeWidth={2.2} fill={saved ? 'currentColor' : 'none'} />
                </button>
              </div>
            );
          })}
          {list.length === 0 && (
            <div className="card empty">
              <p className="empty__title">조건에 맞는 레시피가 없어요</p>
              <p className="empty__body">검색어를 바꾸거나 필터를 줄여 보세요.</p>
              <Link to="/recipes/filter" className="btn btn--primary btn--sm">필터 바꾸기</Link>
            </div>
          )}
        </div>
      </div>

      <TabBar />
    </Screen>
  );
}
