# Frequently Asked Questions
Questions I've received via email or other means and my best attempt at helpful answers.

## Regarding examples/led.asm...
### 1. What is the exact memory address of the red LED's GPIO pin?
### 2. On what line is the red LED's GPIO pin set high?
### 3. What is the purpose of the instruction that "stores the GPIO config"?
I think that a detailed explanation of the program will satisfy all three questions about [examples/led.asm](https://github.com/theandrew168/bronzebeard/blob/master/examples/led.asm).
I'm hoping to provide enough detail as to how I discovered all of these small bits of information necessary to turn on the LED.
In general, though, I extracted the necessary steps from the [GD32VF103_Firmware_Library](https://github.com/riscv-mcu/GD32VF103_Firmware_Library/tree/master/Firmware/GD32VF103_standard_peripheral) and platform-gd32v's [longan-nano-blink example](https://github.com/sipeed/platform-gd32v/blob/master/examples/longan-nano-blink/src/main.c).

Finding this answer to question 1 requires looking at both the [Longan Nano schematic](https://dl.sipeed.com/LONGAN/Nano/HDK/Longan%20Nano%202663/Longan%20nano%202663%28Schematic%29.pdf) and the [GD32VF103 manual](https://gd32mcu.21ic.com/data/documents/shujushouce/GD32VF103_User_Manual_EN_V1.2.pdf).
By looking at sector A5 of the schematic, we can see that the red LED is associated with GPIO port C, pin 13.
Similarly, the green LED is on port A, pin 1 and the blue LED is on port A, pin 2.
It's also important to note here how the 3V3 power is on the opposite side of the GPIO connections meaning that the LEDs are essentially active-low.
When the GPIO is ON, the LED will be OFF and vice versa.
I was stumped by this nuance for days.
Thankfully, someone else also noticed this and [added clarity](https://github.com/sipeed/platform-gd32v/commit/7b85c1eb83b4cf2ff10aa3dae61444741a97479a) to the longan-nano-blink example.
To answer question 2, there is no line in the code that sets the GPIO pin high.
This is because the LED is on when the GPIO pin is OFF (which is the pin's default state).
To be extra clear, you could add a line that explicitly turns off the pin but it's technically redundant.
To turn the LED off, you must explicitly turn the pin on (section 7.5.4, GPIOx_OCTL or section 7.5.5, GPIOx_BOP).

As a small aside, this "bug" was really quite fascinating.
Almost every piece of example code I originally looked at had this backwards.
But, since they all told the LED to blink repeatedly, the device appeared to be working as intended.
The LED was indeed turning on and off, but the logic was inverted!
Very interesting.

Anyhow, with the proper GPIO ports and pins known, we now have to dive into the manual.
Even though the "led.asm" example only uses the red LED on GPIO port C, I enable both A and C to make it easier to swap to the green or blue LEDs.
Since we may want to use both GPIO ports A and C, they both needed to be enabled via the chip's RCU.
This is what happens directly under the "rcu_init" label.
Section 5.3 and 5.3.7 of the manual yields more info about the RCU memory address and register offsets (RCU_BASE_ADDR and RCU_APB2EN_OFFSET).
You can see in the APB2 enable register definition how bits 2 and 4 correspond to GPIO ports A and C, respectively.

Configuring the GPIO pins is a bit more involved.
Section 7.3 describes the 4 bits of config available for each pin (2 bits for mode and 2 bits for control).
For the GPIO pins connected to LEDs, the control needs to be "GPIO Push-pull" (0b00) and the mode needs to be "Speed up to 50MHz" (0b11).
These requirements were simply pulled directly from the longan-nano-blink example.
I'm not a GPIO expert by any means so I don't necessarily know why these settings do the trick.
I just know that they work.

Moving on, we now know what the correct 4 bits are to get the GPIO pin doing what it should.
The next question is where to store these 4 bits.
Section 7.5 details the base address for each of the GPIO ports A-E.
This is where GPIO_BASE_ADDR_C (0x40011000) comes from.
If using the blue or green LEDs, this would need to be swapped for GPIO_BASE_ADDR_A (0x40010800).
Since each GPIO port can support up to 16 pins, that means the total number of config bits is 16 * 4 = 64 bits.
Given that the memory registers on the GD32VF103 are only 32-bits each, 2 of them are needed to cover the entire GPIO pin space.
This is why you see "Port control register 0" and "Port control register 1".
The first handles GPIO pins 0-7 and the second handles pins 8-15.

In the code, the target is specifically the red LED on GPIO port C, pin 13.
Pin 13 lies within the second port control register (GPIOC_CTL1).
Once the 4 config bits are loaded into register t2, they need to be shifted over to the correct "slot".
If no shifting took place, the code would effectively apply the config to pin 8 since pin 8 occupies the least-significant 4 bits of the GPIOC_CTL1 register.
To get to pin 13 we need to shift over by 5 pin configs.
Since each config occupies 4 bits, we need to shift 5 * 4 = 20 bits.
Note that I first set pin 13's 4 config bits to zero before applying the new config.
This is to be sure that the adjacent GPIO configs don't get changed unintentionally.
It probably wouldn't be an issue for this small example but as more GPIO pins get utilized, I don't want this code to set a naive example.

Okay, question 3!
The general flow of the pin config process is as follows: load the existing GPIOC_CTL1 config value, make any necessary changes, then store the value back to GPIOC_CTL1.
In this example, t0 holds the address of the GPIOC_CTL1 register and t1 holds the value being worked on.
Storing the config back to memory is necessary to have it take effect.
Given that RISC-V is a load/store architecture, this general flow is likely to be seen all over the place.
