# -*- coding: utf-8 -*-
"""
Allosta Partners. Гибридная модель: розничный колокейшн Tier III в Алматы
(4,0 МВт ИТ, 2027-2036) плюс собственный ИТ-блок под управляемые услуги
на части той же ёмкости.

Расширяет `tsod-almaty-colo-model.py` параметрами mix_*. При пустом mix_add
воспроизводит базовую модель в точности (IRR на капитал 17,1 %).

Запуск:  python3 tsod-almaty-hybrid-model.py

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
    # --- собственный ИТ-блок под управляемые услуги (гибрид) ---
    mix_add={},                    # {год: +МВт ИТ под своё железо}, берётся из той же ёмкости
    mix_capex_mw=35.0,             # $ млн на МВт серверов, СХД и сети
    mix_price=1100.0,              # $/кВт/мес за управляемые услуги
    mix_price_esc=-0.02,           # цена вычислений падает в долларах
    mix_ramp=[.35, .65, .80, .85], # выход на загрузку блока
    mix_draw=0.75,                 # фактический отбор мощности своим железом
    mix_life=5, mix_refresh=0.85,  # срок службы и стоимость замены к первоначальной
    mix_lic=0.12, mix_sales=0.10,  # лицензии и продажи, доля выручки блока
    mix_maint=0.08,                # ТОиР железа, доля от его стоимости
    mix_staff_mw=0.70,             # $ млн в год на МВт собственного блока
    mix_tax_dep=0.40,              # группа III НК РК, убывающий остаток
    mix_exit_mult=5.0,             # мультипликатор EBITDA услуг на выходе
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

    # --- собственный ИТ-блок: мощность, выручка, capex, замена парка ---
    mix = p['mix_add'] or {}
    mix_y0 = min(mix) if mix else None
    mix_mw = z(); mix_kw = z(); mix_rev = z(); mix_capex = z(); mix_cost = z()
    for i, y in enumerate(YEARS):
        tot_mw = 0.0; sold_kw = 0.0; cost = 0.0
        for sy, mw in mix.items():
            if y >= sy:
                tot_mw += mw; cost += mw*p['mix_capex_mw']
                age = y - sy
                r = p['mix_ramp'][age] if age < len(p['mix_ramp']) else p['mix_ramp'][-1]
                sold_kw += mw*1000*r
        mix_mw[i] = tot_mw; mix_kw[i] = sold_kw; mix_cost[i] = cost
        if mix_y0 is not None and y >= mix_y0:
            pr = p['mix_price']*(1+p['mix_price_esc'])**(y-mix_y0)
            mix_rev[i] = sold_kw*pr*12/1e6
    for sy, mw in mix.items():
        if sy in idx: mix_capex[idx[sy]] += mw*p['mix_capex_mw']
        ry = sy + p['mix_life']
        if ry in idx: mix_capex[idx[ry]] += mw*p['mix_capex_mw']*p['mix_refresh']
    capex_fac = list(capex)
    for i in range(n): capex[i] += mix_capex[i]

    # --- выручка ---
    rev = z(); billed_kw = z(); colo_rev = z()
    for i, y in enumerate(YEARS):
        price = p['price0']*(1+p['price_esc'])**max(0, y-p['ph1_cod'])
        kw = 0.0
        if y >= p['ph1_cod']:
            occ = p['occ_ph1'].get(y, p['occ_stab'])
            kw += p['ph1_mw']*1000*occ
        if y >= p['ph2_cod']:
            occ = p['occ_ph2'].get(y, p['occ_stab'])
            kw += p['ph2_mw']*1000*occ
        inst = (p['ph1_mw'] if y >= p['ph1_cod'] else 0) + (p['ph2_mw'] if y >= p['ph2_cod'] else 0)
        mw_live[i] = inst
        occb = kw/(inst*1000) if inst > 0 else 0.0
        kw = max(0.0, (inst - mix_mw[i]))*1000*occb      # колокейшн на оставшейся ёмкости
        billed_kw[i] = kw
        colo_rev[i] = kw*price*12/1e6
        rev[i] = colo_rev[i] + mix_rev[i]

    # --- opex ---
    cum_capex = z(); cum_eq = z(); acc = 0.0
    for i in range(n):
        acc += capex_fac[i]; cum_capex[i] = acc; cum_eq[i] = acc*0.70

    nbv = z(); dep = z(); book = {'b':0.0,'e':0.0,'o':0.0}
    mix_book = []          # [(год ввода, стоимость)] для линейной амортизации за mix_life
    for i in range(n):
        c = capex_fac[i]
        book['b'] += c*p['split_bld']; book['e'] += c*p['split_eq']; book['o'] += c*p['split_oth']
        d = book['b']/p['life_bld'] + book['e']/p['life_eq'] + book['o']/p['life_oth']
        dep[i] = d if YEARS[i] >= p['ph1_cod'] else 0.0
        nbv[i] = (nbv[i-1] if i else 0.0) + c - dep[i]          # база налога на имущество: только объект
        if mix_capex[i] > 0: mix_book.append((i, mix_capex[i]))
    mix_dep = z()
    for st, c in mix_book:
        for k in range(st, min(n, st+p['mix_life'])):
            mix_dep[k] += c/p['mix_life']
    for i in range(n): dep[i] += mix_dep[i]

    elec = z(); staff = z(); maint = z(); ins = z(); ptax = z(); other = z(); sga = z(); opex = z(); ebitda = z()
    mix_ebitda = z()
    for i, y in enumerate(YEARS):
        if rev[i] == 0:
            continue
        t = p['tariff0']*(1+p['tariff_esc'])**(y-p['ph1_cod'])
        kwh = (billed_kw[i]*p['draw'] + mix_kw[i]*p['mix_draw'])*p['pue']*8760
        elec[i] = kwh*t/1e6
        esc = (1+p['opex_esc'])**(y-p['ph1_cod'])
        staff[i] = (p['staff_ph1'] + (p['staff_ph2'] if y >= p['ph2_cod'] else 0)
                    + p['mix_staff_mw']*mix_mw[i])*esc
        maint[i] = cum_eq[i]*p['maint_rate'] + mix_cost[i]*p['mix_maint']
        ins[i]   = (cum_capex[i] + mix_cost[i])*p['ins_rate']
        ptax[i]  = nbv[i]*p['prop_tax']
        other[i] = (p['land']+p['net'])*esc
        sga[i]   = colo_rev[i]*(p['sga_rate']+p['baddebt_rate']) \
                 + mix_rev[i]*(p['mix_lic']+p['mix_sales']+p['baddebt_rate'])
        opex[i]  = elec[i]+staff[i]+maint[i]+ins[i]+ptax[i]+other[i]+sga[i]
        ebitda[i] = rev[i]-opex[i]
        if mix_rev[i] > 0:
            mix_el = mix_kw[i]*p['mix_draw']*p['pue']*8760*t/1e6
            mix_ebitda[i] = (mix_rev[i] - mix_el - p['mix_staff_mw']*mix_mw[i]*esc
                             - mix_cost[i]*p['mix_maint'] - mix_cost[i]*p['ins_rate']
                             - mix_rev[i]*(p['mix_lic']+p['mix_sales']+p['baddebt_rate']))

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
    tpool = {'b':0.0,'e':0.0,'o':0.0,'m':0.0}; tdep = z(); tax = z(); loss = 0.0; ebt = z()
    for i, y in enumerate(YEARS):
        tpool['b'] += capex_fac[i]*p['split_bld']; tpool['e'] += capex_fac[i]*p['split_eq']
        tpool['o'] += capex_fac[i]*p['split_oth']; tpool['m'] += mix_capex[i]
        if y >= p['ph1_cod']:
            d = (tpool['b']*p['tax_dep_bld'] + tpool['e']*p['tax_dep_eq'] + tpool['o']*p['tax_dep_oth']
                 + tpool['m']*p['mix_tax_dep'])
            tpool['b'] *= (1-p['tax_dep_bld']); tpool['e'] *= (1-p['tax_dep_eq'])
            tpool['o'] *= (1-p['tax_dep_oth']); tpool['m'] *= (1-p['mix_tax_dep'])
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
    fac_fwd = (ebitda[ex]-mix_ebitda[ex])*p['exit_growth']
    svc_fwd = mix_ebitda[ex]*p['exit_growth']
    ev = fac_fwd/p['exit_cap'] + svc_fwd*p['mix_exit_mult']
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
               capex_total=sum(capex), capex_fac=capex_fac, mix_capex=mix_capex, mix_mw=mix_mw,
               mix_rev=mix_rev, mix_ebitda=mix_ebitda, colo_rev=colo_rev, debt_total=d1+d2,
               irr_u=irr(ufcf), irr_e=irr(efcf), npv_h=npv(efcf, p['hurdle']), npv_18=npv(efcf, 0.18),
               moic=(sum(dist)/eq_total if eq_total else None),
               entry_yield=(ebitda[idx[2034]]/sum(capex)))
    return res


# ──────────────────────────────────────────────────────────────────────────
#  Прогон: чистый колокейшн против гибрида с собственным ИТ-блоком
# ──────────────────────────────────────────────────────────────────────────
import copy

def variant(**kw):
    p = copy.deepcopy(P); p.update(kw); return run(p)

MIX = {2030: 0.2, 2033: 0.3}          # базовый гибрид: 0,5 МВт из 4,0 под своё железо

def ln(nm, r):
    dm = min((d for _, d in r['dscr']), default=0)
    print(f"{nm:<44} IRR {r['irr_e']*100:>6.1f} %  MOIC {r['moic']:.2f}x  "
          f"капитал ${r['eq_total']:>5.1f} млн  DSCR {dm:.2f}  capex ${r['capex_total']:.1f} млн")

def report():
    base = variant()
    print("=" * 118)
    print("ГИБРИД: колокейшн плюс собственный ИТ-блок под управляемые услуги")
    print("=" * 118)
    ln("Чистый колокейшн (эталон)", base)
    print()
    print("Размер и график собственного блока, цена услуг $1 100/кВт/мес, железо $35 млн/МВт:")
    for nm, mx in [("0,2 МВт с 2030", {2030: 0.2}),
                   ("0,2 МВт с 2030 + 0,3 МВт с 2033", MIX),
                   ("0,3 МВт с 2030 + 0,3 МВт с 2032", {2030: 0.3, 2032: 0.3}),
                   ("0,5 МВт сразу с 2030", {2030: 0.5}),
                   ("1,0 МВт двумя шагами", {2030: 0.5, 2032: 0.5})]:
        ln("  " + nm, variant(mix_add=mx))
    print()
    print("Матрица: цена управляемых услуг x стоимость железа, IRR на капитал, %")
    caps = [20, 25, 30, 35, 45]
    print("цена \\ железо".ljust(17) + "".join(f"{c:>8}" for c in caps))
    for pr in [1100, 1500, 2000, 2500, 3000, 4000]:
        row = [variant(mix_add=MIX, mix_price=pr, mix_capex_mw=c)['irr_e']*100 for c in caps]
        print(f"${pr:<16}" + "".join(f"{x:>8.1f}" for x in row))
    print()
    print("Цена безразличия: при какой цене услуг гибрид сравнивается с чистым колокейшном")
    for cx in caps:
        lo, hi = 800.0, 9000.0
        f = lambda x: variant(mix_add=MIX, mix_price=x, mix_capex_mw=cx)['irr_e'] - base['irr_e']
        if f(lo)*f(hi) > 0:
            print(f"  железо ${cx} млн/МВт -> решения нет в диапазоне"); continue
        for _ in range(50):
            mid = (lo+hi)/2
            if f(lo)*f(mid) <= 0: hi = mid
            else: lo = mid
        x = (lo+hi)/2
        print(f"  железо ${cx:>2} млн/МВт -> ${x:>6.0f}/кВт/мес = {x/P['price0']:.1f}x к цене колокейшна")
    print()
    print("Что внутри блока в 2035 году при базовых допущениях:")
    r = variant(mix_add=MIX); i = r['YEARS'].index(2035)
    hw = sum(MIX.values())*P['mix_capex_mw']
    print(f"  мощность блока {r['mix_mw'][i]:.2f} МВт из 4,0; выручка ${r['mix_rev'][i]:.2f} млн; "
          f"EBITDA ${r['mix_ebitda'][i]:.2f} млн")
    print(f"  стоимость железа ${hw:.1f} млн; обновление парка каждые {P['mix_life']} лет = "
          f"${hw*P['mix_refresh']/P['mix_life']:.2f} млн в год")
    print(f"  EBITDA проекта ${r['ebitda'][i]:.2f} млн против ${base['ebitda'][i]:.2f} млн у чистого колокейшна")
    print(f"  capex ${r['capex_total']:.1f} млн против ${base['capex_total']:.1f} млн; "
          f"капитал ${r['eq_total']:.1f} млн против ${base['eq_total']:.1f} млн")

if __name__ == "__main__":
    report()
