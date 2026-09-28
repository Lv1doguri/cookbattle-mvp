import { useEffect, useState } from 'react';
import { Screen, Header, TopBar } from '../components/Screen';
import TabBar from '../components/TabBar';
import Icon from '../components/Icon';
import { Badge, Button, Coin, PointPill, ProgressBar } from '../components/ui';
import { adaptShopItem } from '../api/adapt';
import { SHOP_ITEMS, won } from '../data/mock';
import { useApp } from '../state/AppContext';

// The API doesn't carry icon/color; match by name to the design's fixed 4 items for visuals.
function withVisuals(item) {
  const mock = SHOP_ITEMS.find((m) => m.name === item.name) ?? SHOP_ITEMS[0];
  return { ...item, icon: mock.icon, bg: mock.bg, ink: mock.ink };
}

export default function Shop() {
  const { user, fetchShop, redeem } = useApp();
  const [items, setItems] = useState(null);
  const [selected, setSelected] = useState(null); // item being confirmed
  const [done, setDone] = useState(null); // item just redeemed
  const [error, setError] = useState('');

  useEffect(() => {
    fetchShop().then((raw) => setItems(raw.map(adaptShopItem).map(withVisuals))).catch(() => setItems([]));
  }, [fetchShop]);

  const confirm = async () => {
    setError('');
    try {
      const r = await redeem(selected.id);
      setDone({ ...selected, points: r.points });
    } catch (e) {
      setError(e.message);
    } finally {
      setSelected(null);
    }
  };

  if (!user) return null;

  return (
    <Screen>
      <Header className="shop-hdr">
        <TopBar title="상점" brand>
          <PointPill points={user.points} />
        </TopBar>
        <div className="shop-level">
          <Badge className="shop-level__badge">Lv.{user.level}</Badge>
          <span className="shop-level__text">
            <span>레벨이 오르면 더 많은 기프티콘이 열려요</span>
            <ProgressBar value={user.levelProgress} variant="brand" />
          </span>
        </div>
      </Header>

      <div className="body">
        <h2 className="shop-title">기프티콘</h2>
        {items === null ? (
          <p className="muted" style={{ padding: '16px' }}>불러오는 중…</p>
        ) : (
          <div className="gift-grid">
            {items.map((item) => (
              <div key={item.id} className="g">
                <div className="gi" style={item.photoUrl ? undefined : { background: `linear-gradient(135deg, ${item.bg[0]}, ${item.bg[1]})`, color: item.ink }}>
                  {item.photoUrl ? (
                    <img src={item.photoUrl} alt="" className="gi__img" style={item.locked ? { opacity: 0.6 } : undefined} />
                  ) : (
                    <Icon name={item.icon} size={40} strokeWidth={1.8} style={item.locked ? { opacity: 0.55 } : undefined} />
                  )}
                  {item.locked && <span className="gi__lock"><Icon name="lock" size={14} strokeWidth={2.4} /></span>}
                </div>
                <div className="gn">{item.name}</div>
                <div className="gp">{won(item.price)}P</div>
                {item.locked ? (
                  <button type="button" className="gb off" disabled>Lv.{item.minLevel}부터 교환 가능</button>
                ) : item.soldOut ? (
                  <button type="button" className="gb off" disabled>이번 달 품절</button>
                ) : item.short > 0 ? (
                  <button type="button" className="gb off" disabled>{won(item.short)}P 더 필요해요</button>
                ) : (
                  <button type="button" className="gb" onClick={() => setSelected(item)}>교환</button>
                )}
              </div>
            ))}
          </div>
        )}
        {error && <p className="muted" style={{ color: 'var(--danger, #d64545)' }}>{error}</p>}
        <p className="note" style={{ marginBottom: 20 }}>포인트는 매일 대결 참가(+3P)와 순위 보상으로 모여요</p>
      </div>

      <TabBar />

      {selected && (
        <>
          <div className="scrim" onClick={() => setSelected(null)} />
          <div className="sheet" role="dialog" aria-modal="true" aria-label={`${selected.name} 교환`}>
            <span className="sheet__grip" />
            <span
              className="sheet__ico"
              style={selected.photoUrl ? { overflow: 'hidden' } : { background: `linear-gradient(135deg, ${selected.bg[0]}, ${selected.bg[1]})`, color: selected.ink }}
            >
              {selected.photoUrl ? <img src={selected.photoUrl} alt="" className="gi__img" /> : <Icon name={selected.icon} size={42} strokeWidth={1.8} />}
            </span>
            <h2 className="sheet__title">{selected.name}</h2>
            <p className="sheet__sub">교환하면 포인트가 바로 차감돼요</p>
            <div className="kv-box">
              <div className="kv"><span>필요 포인트</span><b>{won(selected.price)}P</b></div>
              <div className="kv"><span>보유 포인트</span><b>{won(user.points)}P</b></div>
              <div className="kv-box__rule" />
              <div className="kv"><span>교환 후</span><b className="kv__after">{won(user.points - selected.price)}P</b></div>
            </div>
            <div className="sheet__actions">
              <Button variant="muted" onClick={() => setSelected(null)}>취소</Button>
              <Button onClick={confirm} autoFocus>교환하기</Button>
            </div>
          </div>
        </>
      )}

      {done && (
        <>
          <div className="scrim" />
          <div className="dialog" role="alertdialog" aria-modal="true" aria-label="교환 완료">
            <div className="dialog__glow" />
            <span className="dialog__check"><Icon name="check" size={38} strokeWidth={2.8} /></span>
            <h2 className="dialog__title">교환 완료!</h2>
            <p className="dialog__body">{done.name}을 교환했어요.<br />교환 내역이 저장됐어요.</p>
            <div className="dialog__remain">
              <span>남은 포인트</span>
              <b><Coin />{won(done.points)}P</b>
            </div>
            <p className="dialog__fine">MVP 단계에서는 실제 기프티콘이 발송되지 않아요</p>
            <Button onClick={() => setDone(null)} style={{ marginTop: 18 }} autoFocus>확인</Button>
          </div>
        </>
      )}
    </Screen>
  );
}
