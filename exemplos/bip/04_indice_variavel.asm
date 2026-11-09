.data
v0 : 0, 0, 0, 0, 0
v1 : 0
t0 : 0
t1 : 0

.text
    LDI 2
    STO v1
    LD v1
    STO t0
    LDI 50
    STO t1
    LD t0
    STO $indr
    LD t1
    STOV v0
    LD v1
    STO $indr
    LDV v0
    STO $out_port
    HLT
