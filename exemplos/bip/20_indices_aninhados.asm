.data
v0 : 0, 0, 0
v1 : 0, 0
t0 : 0
t1 : 0

.text
    LDI 0
    STO t0
    LDI 0
    STO $indr
    LD t0
    STOV v0
    LDI 1
    STO $indr
    LD t0
    STOV v0
    LDI 2
    STO $indr
    LD t0
    STOV v0
    LDI 1
    STO t0
    LDI 0
    STO $indr
    LD t0
    STOV v1
    LDI 1
    STO $indr
    LD t0
    STOV v1
    LDI 0
    STO $indr
    LDV v1
    STO t0
    LDI 0
    STO $indr
    LDV v0
    STO $indr
    LDV v1
    STO t1
    LD t0
    STO $indr
    LD t1
    STOV v0
    LDI 1
    STO $indr
    LDV v0
    STO $out_port
    HLT
