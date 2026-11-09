.data
v0 : 0, 0, 0, 0
t0 : 0
t1 : 0

.text
    LDI 0
    STO t0
    LDI 2
    STO t1
    LD t0
    STO $indr
    LD t1
    STOV v0
    LDI 0
    STO $indr
    LDV v0
    STO t0
    LD $in_port
    STO t1
    LD t0
    STO $indr
    LD t1
    STOV v0
    LDI 2
    STO $indr
    LDV v0
    STO $out_port
    HLT
