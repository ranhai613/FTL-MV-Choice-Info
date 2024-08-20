local vter_with_i_n = function (cvec)
	local i = -1
	local n = cvec:size()
	return function()
		i = i + 1
		if i < n then return cvec[i], i, n end
	end
end

local get_INFO_parser = function (full)
	return function (text)
		text = text:sub(7, -8)
		local name = text:match('%[NAME%].-%[/NAME%]')
		if name == nil then
			return ''
		end
		local value = Hyperspace.metaVariables['choiceInfo_event_'..name:sub(7, -8)]
		if (value == 1) or full then
			return '\n'..text:gsub('%[NAME%].-%[/NAME%]', '')
		else
			return ''
		end
	end
end

local get_FightINFO_parser = function (full)
	return function (text)
		local is_worthShowing = false
		local info_parser = get_INFO_parser(full)
		text = text:sub(12, -13)
		text = text:gsub('%[INFO%].-%[/INFO%]', function (info)
			info = info_parser(info)
			if info ~= '' then
				is_worthShowing = true
			end
			return info:gsub('\n', ' ')
		end)
		if is_worthShowing then
			return '\n'..text
		else
			return ''
		end
	end
end

local parse = function (text, full)
	text = text:gsub('%[FightINFO%].-%[/FightINFO%]', get_FightINFO_parser(full))
	text = text:gsub('%[INFO%].-%[/INFO%]', get_INFO_parser(full))
	return text
end

script.on_internal_event(Defines.InternalEvents.PRE_CREATE_CHOICEBOX, function(event)
    local Choices = event:GetChoices()
	local fullInfo = '--------[Full Info]--------'
    for choice, i, n in vter_with_i_n(Choices) do
		if choice.text.isLiteral == false then
			choice.text.data = choice.text:getText()
			choice.text.isLiteral = true
		end
		local original_text = choice.text.data
        choice.text.data = parse(original_text, false)
		fullInfo = fullInfo..'\n\n'..tostring(i + 1)..'. '..parse(original_text, true)
		if ((n - i) == 1) and (Hyperspace.metaVariables['choiceInfo_bottom_fullInfo'] == 1) then
			choice.text.data = choice.text.data..string.rep('\n', 15)..fullInfo
		end
    end
end)
