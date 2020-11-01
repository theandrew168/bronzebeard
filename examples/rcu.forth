\ define RCU base address
: 0x40021000 1 256* 256* 256* 16* 4* 1 256* 256* 2* 1 256* 16* or or ;
: RCU_BASE_ADDR 0x40021000 ;

\ define RCU ABP2 enable offset
: 0x18 1 16* 1 4* 2* or ;
: RCU_APB2EN_OFFSET 0x18 ;

\ enable RCU for the bit pattern on top of the stack
: rcu_enable RCU_BASE_ADDR RCU_APB2EN_OFFSET + ! ;

\ define RCU enable constants for GPIO ports
: RCU_GPIO_A 1 2* 2* ;
: RCU_GPIO_B 1 2* 2* 2* ;
: RCU_GPIO_C 1 2* 2* 2* 2* ;
: RCU_GPIO_D 1 2* 2* 2* 2* 2* ;
: RCU_GPIO_E 1 2* 2* 2* 2* 2* 2* ;

\ enable RCU for GPIO ports A and C
RCU_GPIO_A RCU_GPIO_C or rcu_enable
