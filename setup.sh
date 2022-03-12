echo "start setting up"

iptables -P OUTPUT DROP \
&& iptables -A OUTPUT -p tcp --sport 7590 -j ACCEPT \
&& iptables -P INPUT DROP \
&& iptables -A INPUT -p tcp -s 172.19.0.0/24 -j ACCEPT \
&& echo "iptables setup done"

adduser --disabled-password -g "executor" executor \
&& echo "add user executor done"

su executor -c "graphery_executor server -u 0.0.0.0"
echo "done executing"

echo "bye~ :)"
