// Copyright (c) 2025 texer.ai. All rights reserved.
#ifndef LOGIC_FUZZER_H_
#define LOGIC_FUZZER_H_

#include <cstdint>

namespace lf
{
    class LogicFuzzer
    {
    public:
        uint8_t Congest() const;

        // Constructor control.
        LogicFuzzer();
        LogicFuzzer(uint32_t seed);
        ~LogicFuzzer();

    private:
        struct LogicFuzzerImpl;
        LogicFuzzerImpl* pimpl_ = nullptr;
    };
}

#endif // LOGIC_FUZZER_H_