echo "start setting up"

iptables -P OUTPUT DROP \
&& iptables -A OUTPUT -p tcp --sport "$GE_SERVER_PORT" -j ACCEPT \
&& iptables -P INPUT DROP \
&& iptables -A INPUT -p tcp -s "$(hostname -i)/24" -j ACCEPT \
&& echo "iptables setup done"

su executor -c "graphery_executor server -u 0.0.0.0"
echo "done executing"

echo "bye~ :)"
