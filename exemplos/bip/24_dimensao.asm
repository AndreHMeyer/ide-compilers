.data
v0 : 0, 0, 0, 0, 0
t0 : 0
t1 : 0

.text
    LDI 4
    STO t0
    LDI 40
    STO t1
    LD t0
    STO $indr
    LD t1
    STOV v0
    LDI 4
    STO $indr
    LDV v0
    STO $out_port
    HLT
