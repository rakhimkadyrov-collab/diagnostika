# -*- coding: utf-8 -*-
"""
Allosta Partners. Модель инвестиционного проекта:
розничный колокейшн Tier III, Алматы, 4,0 МВт ИТ, горизонт 2027-2036.

Запуск:  python3 tsod-almaty-colo-model.py

Все допущения собраны в словаре P и помечены статусами в заключении
`tsod-almaty-colocation-ic.html`, раздел 14 «Верификация».
Файл воспроизводит каждую цифру заключения, включая матрицу чувствительности,
сценарии и варианты горизонта выхода.
"""

YEARS = list(range(2027, 2037))           # 10 лет
FX    = 452.12                            # ₸/$ (НБРК, 17.10.2026)

P = dict(
    # --- периметр ---
    ph1_mw=2.0, ph2_mw=2.0,
    ph1_capex_split={2027: .45, 2028: .55},
    ph2_capex_split={2030: .50, 2031: .50},
    ph1_cod=2029, ph2_cod=2032,
    # --- capex, $ млн на МВт ИТ ---
    ph1_capex_mw=10.5,                    # 1-я очередь несёт общую инфраструктуру
    ph2_capex_mw=9.5,
    preopen=0.9,                          # $ млн: подбор персонала, маркетинг, сертификация Tier III
    # --- цена и заполняемость ---
    price0=280.0,                         # $/кВт/мес на дату ввода 1-й очереди
    price_esc=0.015,                      # +1,5 % в год в долларах (₸ +5,5 % минус девальвация 4 %)
    occ_ph1={2029:.70, 2030:.82, 2031:.88},
    occ_ph2={2032:.45, 2033:.70, 2034:.85, 2035:.88},
    occ_stab=.88,
    # --- операционные расходы ---
    pue=1.35,
    draw=0.55,                            # фактический отбор мощности к законтрактованной
    tariff0=0.055,                        # $/кВт·ч в 2029 году
    tariff_esc=0.04,
    staff_ph1=0.60, staff_ph2=0.34,       # $ млн в год
    opex_esc=0.04,
    maint_rate=0.020,                     # % от оборудования (70 % capex)
    ins_rate=0.0035,
    prop_tax=0.015,                       # налог на имущество, % от балансовой стоимости
    land=0.06, net=0.12,                  # земля/аренда, связность, $ млн
    sga_rate=0.05, baddebt_rate=0.005,
    # --- амортизация ---
    split_bld=.30, split_eq=.60, split_oth=.10,
    life_bld=25, life_eq=12, life_oth=7,
    tax_dep_bld=.10, tax_dep_eq=.25, tax_dep_oth=.15,   # НК РК, убывающий остаток
    kpn=0.20, vat=0.12,
    # --- финансирование ---
    debt_share=0.45, rate=0.11, ph1_amort=12, ph2_amort=12,
    dsra_months=6,
    # --- выход ---
    exit_cap=0.15, exit_cost=0.02, exit_growth=1.02,
    hurdle=0.25,                          # Kill Criteria AP: 25 % IRR
    exit_year=2036,
)

def irr(cf, lo=-0.95, hi=3.0):
    def npv(r): return sum(c/(1+r)**i for i, c in enumerate(cf))
    if npv(lo)*npv(hi) > 0: return None
    for _ in range(300):
        m = (lo+hi)/2
        if npv(lo)*npv(m) <= 0: hi = m
        else: lo = m
    return (lo+hi)/2

def npv(cf, r): return sum(c/(1+r)**i for i, c in enumerate(cf))

def run(p, verbose=False):
    y0 = YEARS[0]
    n  = len(YEARS)
    z  = lambda: [0.0]*n
    idx = {y: i for i, y in enumerate(YEARS)}

    capex = z(); mw_live = z()
    ph1_capex = p['ph1_mw']*p['ph1_capex_mw']
    ph2_capex = p['ph2_mw']*p['ph2_capex_mw']
    for y, s in p['ph1_capex_split'].items(): capex[idx[y]] += ph1_capex*s
    for y, s in p['ph2_capex_split'].items(): capex[idx[y]] += ph2_capex*s
    capex[idx[p['ph1_cod']-1]] += p['preopen']

    # --- выручка ---
    rev = z(); billed_kw = z()
    for i, y in enumerate(YEARS):
        price = p['price0']*(1+p['price_esc'])**max(0, y-p['ph1_cod'])
        kw = 0.0
        if y >= p['ph1_cod']:
            occ = p['occ_ph1'].get(y, p['occ_stab'])
            kw += p['ph1_mw']*1000*occ
        if y >= p['ph2_cod']:
            occ = p['occ_ph2'].get(y, p['occ_stab'])
            kw += p['ph2_mw']*1000*occ
        billed_kw[i] = kw
        rev[i] = kw*price*12/1e6
        mw_live[i] = (p['ph1_mw'] if y >= p['ph1_cod'] else 0) + (p['ph2_mw'] if y >= p['ph2_cod'] else 0)

    # --- opex ---
    cum_capex = z(); cum_eq = z(); acc = 0.0
    for i in range(n):
        acc += capex[i]; cum_capex[i] = acc; cum_eq[i] = acc*0.70

    nbv = z(); dep = z(); pools = {'b':0.0,'e':0.0,'o':0.0}; book = {'b':0.0,'e':0.0,'o':0.0}
    for i in range(n):
        c = capex[i]
        book['b'] += c*p['split_bld']; book['e'] += c*p['split_eq']; book['o'] += c*p['split_oth']
        d = book['b']/p['life_bld'] + book['e']/p['life_eq'] + book['o']/p['life_oth']
        dep[i] = d if YEARS[i] >= p['ph1_cod'] else 0.0
        nbv[i] = (nbv[i-1] if i else 0.0) + c - dep[i]

    elec = z(); staff = z(); maint = z(); ins = z(); ptax = z(); other = z(); sga = z(); opex = z(); ebitda = z()
    for i, y in enumerate(YEARS):
        if rev[i] == 0:
            continue
        t = p['tariff0']*(1+p['tariff_esc'])**(y-p['ph1_cod'])
        kwh = billed_kw[i]*p['draw']*p['pue']*8760
        elec[i] = kwh*t/1e6
        esc = (1+p['opex_esc'])**(y-p['ph1_cod'])
        staff[i] = (p['staff_ph1'] + (p['staff_ph2'] if y >= p['ph2_cod'] else 0))*esc
        maint[i] = cum_eq[i]*p['maint_rate']
        ins[i]   = cum_capex[i]*p['ins_rate']
        ptax[i]  = nbv[i]*p['prop_tax']
        other[i] = (p['land']+p['net'])*esc
        sga[i]   = rev[i]*(p['sga_rate']+p['baddebt_rate'])
        opex[i]  = elec[i]+staff[i]+maint[i]+ins[i]+ptax[i]+other[i]+sga[i]
        ebitda[i] = rev[i]-opex[i]

    # --- долг ---
    d1 = ph1_capex*p['debt_share']; d2 = ph2_capex*p['debt_share']
    draw_ = z(); bal = z(); interest = z(); princ = z()
    for y, s in p['ph1_capex_split'].items(): draw_[idx[y]] += d1*s
    for y, s in p['ph2_capex_split'].items(): draw_[idx[y]] += d2*s
    a1 = d1/p['ph1_amort']; a2 = d2/p['ph2_amort']
    b = 0.0
    for i, y in enumerate(YEARS):
        opening = b + draw_[i]
        pr = 0.0
        if p['ph1_cod'] <= y <= p['ph1_cod']+p['ph1_amort']-1: pr += a1
        if p['ph2_cod'] <= y <= p['ph2_cod']+p['ph2_amort']-1: pr += a2
        pr = min(pr, opening)
        interest[i] = (b + draw_[i]*0.5)*p['rate']
        princ[i] = pr; b = opening - pr; bal[i] = b

    # --- налоги: НК РК, убывающий остаток, перенос убытка ---
    tpool = {'b':0.0,'e':0.0,'o':0.0}; tdep = z(); tax = z(); loss = 0.0; ebt = z()
    for i, y in enumerate(YEARS):
        tpool['b'] += capex[i]*p['split_bld']; tpool['e'] += capex[i]*p['split_eq']; tpool['o'] += capex[i]*p['split_oth']
        if y >= p['ph1_cod']:
            d = tpool['b']*p['tax_dep_bld'] + tpool['e']*p['tax_dep_eq'] + tpool['o']*p['tax_dep_oth']
            tpool['b'] *= (1-p['tax_dep_bld']); tpool['e'] *= (1-p['tax_dep_eq']); tpool['o'] *= (1-p['tax_dep_oth'])
            tdep[i] = d
        base = ebitda[i] - tdep[i] - interest[i]
        ebt[i] = ebitda[i] - dep[i] - interest[i]
        if base < 0:
            loss += -base; base = 0.0
        elif loss > 0:
            use = min(loss, base); base -= use; loss -= use
        tax[i] = base*p['kpn']

    # --- НДС по capex: уплата сразу, возврат 60/40 ---
    vat_out = z(); vat_in = z()
    for i in range(n):
        v = capex[i]*p['vat']; vat_out[i] += v
        if i+1 < n: vat_in[i+1] += v*0.6
        if i+2 < n: vat_in[i+2] += v*0.4
    vat_net = [vat_in[i]-vat_out[i] for i in range(n)]

    # --- DSRA ---
    dsra = z()
    for i, y in enumerate(YEARS):
        ds = interest[i]+princ[i]
        dsra[i] = ds*p['dsra_months']/12 if bal[i] > 0 else 0.0
    dsra_flow = [dsra[i]-(dsra[i-1] if i else 0.0) for i in range(n)]

    # --- выход ---
    ex = idx[p['exit_year']]
    noi_fwd = ebitda[ex]*p['exit_growth']
    ev = noi_fwd/p['exit_cap']
    exit_net = ev*(1-p['exit_cost']) - bal[ex] + dsra[ex]

    # --- потоки ---
    ufcf = z(); efcf = z(); cfads = z(); dscr = []
    uloss = 0.0
    for i in range(n):
        b_ = ebitda[i]-tdep[i]
        if YEARS[i] < p['ph1_cod']: b_ = 0.0
        if b_ < 0: uloss += -b_; b_ = 0.0
        elif uloss > 0:
            use = min(uloss, b_); b_ -= use; uloss -= use
        tax_unlev = b_*p['kpn']
        ufcf[i] = ebitda[i] - tax_unlev - capex[i] + vat_net[i]
        cfads[i] = ebitda[i] - tax[i]
        ds = interest[i]+princ[i]
        if ds > 0 and ebitda[i] > 0: dscr.append((YEARS[i], cfads[i]/ds))
        efcf[i] = cfads[i] - ds - capex[i] + draw_[i] + vat_net[i] - dsra_flow[i]
    ufcf[ex] += ev*(1-p['exit_cost'])
    efcf[ex] += exit_net
    ufcf = ufcf[:ex+1]; efcf = efcf[:ex+1]

    equity = [-min(0.0, f) for f in efcf]
    eq_total = sum(equity)
    dist = [max(0.0, f) for f in efcf]

    res = dict(YEARS=YEARS, capex=capex, rev=rev, opex=opex, ebitda=ebitda, elec=elec, staff=staff,
               maint=maint, ins=ins, ptax=ptax, other=other, sga=sga, dep=dep, tdep=tdep, ebt=ebt,
               tax=tax, interest=interest, princ=princ, bal=bal, draw=draw_, vat_net=vat_net,
               ufcf=ufcf, efcf=efcf, cfads=cfads, dscr=dscr, mw_live=mw_live, billed_kw=billed_kw,
               ev=ev, exit_net=exit_net, eq_total=eq_total, dist=dist, nbv=nbv,
               capex_total=sum(capex), debt_total=d1+d2,
               irr_u=irr(ufcf), irr_e=irr(efcf), npv_h=npv(efcf, p['hurdle']), npv_18=npv(efcf, 0.18),
               moic=(sum(dist)/eq_total if eq_total else None),
               entry_yield=(ebitda[idx[2034]]/sum(capex)))
    return res


# ──────────────────────────────────────────────────────────────────────────
#  Прогон: базовый сценарий, чувствительность, сценарии, горизонты выхода
# ──────────────────────────────────────────────────────────────────────────
import copy

def variant(**kw):
    p = copy.deepcopy(P); p.update(kw); return run(p)

def report():
    r = variant(); Yl = r['YEARS']
    def line(nm, a, dec=2):
        print(f"{nm:<30}" + "".join(f"{v:>9.{dec}f}" for v in a))
    print("=" * 120)
    print("БАЗОВЫЙ СЦЕНАРИЙ. Розничный колокейшн Tier III, Алматы, 4,0 МВт ИТ, $ млн")
    print("=" * 120)
    print("ГОД".ljust(30) + "".join(f"{y:>9}" for y in Yl))
    for nm, k in [("Capex", "capex"), ("МВт введено", "mw_live"), ("Выручка", "rev"),
                  ("  электроэнергия", "elec"), ("  персонал", "staff"), ("  ТОиР и ЗИП", "maint"),
                  ("  страхование", "ins"), ("  налог на имущество", "ptax"), ("  прочие", "other"),
                  ("  администрирование", "sga"), ("Операционные расходы", "opex"), ("EBITDA", "ebitda"),
                  ("Амортизация бухгалтерская", "dep"), ("Амортизация налоговая", "tdep"),
                  ("Проценты", "interest"), ("Погашение долга", "princ"), ("Остаток долга", "bal"),
                  ("КПН", "tax"), ("НДС нетто", "vat_net"),
                  ("Поток проекта (без долга)", "ufcf"), ("Поток на капитал", "efcf")]:
        line(nm, r[k])
    print()
    print(f"Capex всего                   ${r['capex_total']:.2f} млн")
    print(f"Долг                          ${r['debt_total']:.2f} млн")
    print(f"Капитал AP                    ${r['eq_total']:.2f} млн")
    print(f"EBITDA 2034                   ${r['ebitda'][Yl.index(2034)]:.2f} млн, "
          f"маржа {r['ebitda'][Yl.index(2034)]/r['rev'][Yl.index(2034)]*100:.1f} %")
    print(f"Доходность на входе           {r['entry_yield']*100:.1f} %")
    print(f"Оценка на выходе              ${r['ev']:.2f} млн, в капитал ${r['exit_net']:.2f} млн")
    print(f"IRR проекта / на капитал      {r['irr_u']*100:.1f} % / {r['irr_e']*100:.1f} %")
    print(f"MOIC                          {r['moic']:.2f}x")
    print(f"NPV при 25 % / при 18 %       ${r['npv_h']:.2f} млн / ${r['npv_18']:.2f} млн")
    print("DSCR: " + ", ".join(f"{y}:{v:.2f}" for y, v in r['dscr']))

    print()
    print("МАТРИЦА ЧУВСТВИТЕЛЬНОСТИ: IRR на капитал, %")
    caps = [(9.0, 8.2, "8,6"), (10.5, 9.5, "10,0"), (11.7, 10.6, "11,2"), (12.9, 11.6, "12,26")]
    print("цена \\ capex".ljust(16) + "".join(f"{c[2]:>9}" for c in caps))
    for pr in [240, 260, 280, 300, 320, 360, 400]:
        vals = [variant(price0=pr, ph1_capex_mw=c[0], ph2_capex_mw=c[1])['irr_e']*100 for c in caps]
        print(f"${pr:<15}" + "".join(f"{x:>9.1f}" for x in vals))

    print()
    print("СЦЕНАРИИ")
    SC = [("Стресс    30 %", dict(price0=245, ph1_capex_mw=12.0, ph2_capex_mw=10.9, exit_cap=.18,
            occ_stab=.80, occ_ph1={2029:.55, 2030:.70, 2031:.78},
            occ_ph2={2032:.35, 2033:.58, 2034:.72, 2035:.80})),
          ("База      50 %", dict()),
          ("Апсайд    20 %", dict(price0=330, ph1_capex_mw=9.3, ph2_capex_mw=8.5, exit_cap=.13,
            kpn=0.0, rate=0.085))]
    w = [.3, .5, .2]; tot = 0.0
    for (nm, kw), wi in zip(SC, w):
        x = variant(**kw); tot += wi*x['irr_e']
        print(f"{nm:<16} IRR {x['irr_e']*100:>6.1f} %   MOIC {x['moic']:.2f}x   "
              f"капитал ${x['eq_total']:.1f} млн   мин. DSCR {min(d for _, d in x['dscr']):.2f}")
    print(f"{'Взвешенно':<16} IRR {tot*100:>6.1f} %   порог AP 25 %")

    print()
    print("ГОРИЗОНТ ВЫХОДА")
    for nm, kw in [("10 лет, 4 МВт, 2036", {}), ("8 лет, 2034", dict(exit_year=2034)),
                   ("6 лет, 2 МВт, 2032", dict(ph2_mw=0.0001, ph2_capex_mw=0.0, exit_year=2032, staff_ph2=0.0)),
                   ("5 лет, 2 МВт, 2031", dict(ph2_mw=0.0001, ph2_capex_mw=0.0, exit_year=2031, staff_ph2=0.0))]:
        x = variant(**kw)
        print(f"{nm:<22} IRR {x['irr_e']*100:>6.1f} %   MOIC {x['moic']:.2f}x   капитал ${x['eq_total']:.1f} млн")

if __name__ == "__main__":
    report()
