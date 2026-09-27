import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Screen, Header, TopBar, BottomAction } from '../components/Screen';
import Icon from '../components/Icon';
import { Button, Chip } from '../components/ui';
import { FILTER_GROUPS } from '../data/mock';
import { useApp } from '../state/AppContext';

export default function Filter() {
  const { filters, setFilters, resetFilters, fetchRecipeCount } = useApp();
  const navigate = useNavigate();
  const [count, setCount] = useState(null);

  useEffect(() => {
    let alive = true;
    fetchRecipeCount({ filters }).then((n) => { if (alive) setCount(n); }).catch(() => { if (alive) setCount(0); });
    return () => { alive = false; };
  }, [filters, fetchRecipeCount]);

  const toggle = (groupId, optId) =>
    setFilters((f) => {
      const cur = f[groupId] ?? [];
      return { ...f, [groupId]: cur.includes(optId) ? cur.filter((x) => x !== optId) : [...cur, optId] };
    });

  return (
    <Screen>
      <Header>
        <TopBar title="필터" back="/recipes">
          <button type="button" className="reset-btn" onClick={resetFilters}>
            <Icon name="refresh" size={14} strokeWidth={2.4} />초기화
          </button>
        </TopBar>
        <Link to="/recipes" className="fridge-cta">
          <span className="fridge-cta__ico"><Icon name="fridge" size={28} color="#fff" /></span>
          <span className="fridge-cta__text">
            <span className="fridge-cta__title">재료로 찾기</span>
            <span className="fridge-cta__desc">냉장고 속 재료로 만들 수 있는<br />요리를 찾아요</span>
          </span>
          <Icon name="chevronRight" size={20} strokeWidth={2.4} color="#fff" />
        </Link>
      </Header>

      <div className="body">
        <div className="card filter-card">
          {FILTER_GROUPS.map((g) => (
            <section key={g.id}>
              <h2 className="sec">{g.title}</h2>
              <div className="wrap">
                {g.options.map((o) => (
                  <Chip key={o.id} withCheck on={filters[g.id]?.includes(o.id)} onClick={() => toggle(g.id, o.id)}>
                    {o.label}
                  </Chip>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>

      <BottomAction className="bottom-action--fade">
        <Button onClick={() => navigate('/recipes')} disabled={count === 0}>
          {count === null ? '불러오는 중…' : count === 0 ? '조건에 맞는 레시피가 없어요' : `레시피 ${count}개 보기`}
        </Button>
      </BottomAction>
    </Screen>
  );
}
