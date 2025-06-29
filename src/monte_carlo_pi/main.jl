module main
using JSON

function monte_carlo_pi(nsample::Int)
    acc = 0
    for _ = 1:nsample
        x = rand() * 2 - 1
        y = rand() * 2 - 1
        if (x * x + y * y) <= 1
            acc += 1
        end
    end
    return 4 * acc / nsample
end

function monte_carlo_pi_threaded(nsample::Int)
    block = nsample / Threads.nthreads()
    acc = Threads.Atomic{Int}(0)
    Threads.@threads for _ in 1:Threads.nthreads()
        value = action(block)
        Threads.atomic_add!(acc, value)
    end
    return 4 * acc[] / nsample
end

function action(nsample)
    acc = 0
    for _ = 1:nsample
        x = rand() * 2 - 1
        y = rand() * 2 - 1
        if (x * x + y * y) <= 1
            acc += 1
        end
    end
    return acc
end

function main_()
    command = ARGS[1]
    nsample = parse(Int, ARGS[2])

    if command == "single"
        start = time_ns()
        pi_result = monte_carlo_pi(nsample)
        end_time = time_ns() - start

        data = Dict(
            "language" => "julia",
            "format" => "single threaded",
            "time" => end_time,
            "cores" => 1,
            "sample" => nsample,
            "pi" => pi_result
        )

        json_string = JSON.json(data)
        println(json_string)
    elseif command == "multi"
        start = time_ns()
        pi_result = monte_carlo_pi_threaded(nsample)
        end_time = time_ns() - start

        data = Dict(
            "language" => "julia",
            "format" => "multi threaded",
            "time" => end_time,
            "cores" => Threads.nthreads(),
            "sample" => nsample,
            "pi" => pi_result
        )

        json_string = JSON.json(data)
        println(json_string)
    else
        println("The command is not valid")
    end

end

main_()
end

